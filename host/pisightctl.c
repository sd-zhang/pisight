/* PiSight UVC settings utility for Linux hosts. SPDX-License-Identifier: MIT */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <linux/usb/video.h>
#include <linux/uvcvideo.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <unistd.h>

static const unsigned char guid[16] = {
	'P','i','S','i','g','h','t','S','e','t','t','i','n','g','s','1'
};

static int extension_unit(const char *video)
{
	char path[PATH_MAX], resolved[PATH_MAX];
	unsigned char descriptors[65536];
	const char *name = strrchr(video, '/');
	size_t count;
	FILE *file;

	name = name ? name + 1 : video;
	if (strncmp(name, "video", 5) || strspn(name + 5, "0123456789") != strlen(name + 5))
		return -1;
	if (snprintf(path, sizeof path, "/sys/class/video4linux/%s/device", name) >= (int)sizeof path ||
	    !realpath(path, resolved))
		return -1;
	for (;;) {
		if (snprintf(path, sizeof path, "%s/descriptors", resolved) < (int)sizeof path &&
		    (file = fopen(path, "rb"))) {
			count = fread(descriptors, 1, sizeof descriptors, file);
			fclose(file);
			for (size_t i = 0; i + 24 <= count && descriptors[i] >= 2;) {
				size_t length = descriptors[i];
				if (i + length > count)
					break;
				if (length >= 24 && descriptors[i + 1] == 0x24 &&
				    descriptors[i + 2] == 0x06 &&
				    !memcmp(descriptors + i + 4, guid, sizeof guid))
					return descriptors[i + 3];
				i += length;
			}
		}
		char *slash = strrchr(resolved, '/');
		if (!slash || slash == resolved)
			break;
		*slash = '\0';
	}
	return -1;
}

static int query(int fd, unsigned char unit, unsigned char request, unsigned char data[8])
{
	struct uvc_xu_control_query q = {
		.unit = unit, .selector = 1, .query = request,
		.size = 8, .data = data,
	};
	return ioctl(fd, UVCIOC_CTRL_QUERY, &q);
}

static void print_settings(const unsigned char data[8])
{
	int ev = (int16_t)(data[2] | (data[3] << 8));
	const char *modes[] = { "off", "on", "activity" };
	printf("{\"fov\":%u,\"ev\":%.1f,\"logo_light\":\"%s\",\"microphone\":%s}\n",
	       data[1], ev / 10.0, modes[data[4]], data[5] ? "true" : "false");
}

static int usage(void)
{
	fputs("Usage: pisightctl /dev/videoN get\n"
	      "       pisightctl /dev/videoN set [--fov 25..75] [--ev -2.0..2.0]"
	      " [--logo off|on|activity] [--mic on|off]\n", stderr);
	return 2;
}

int main(int argc, char **argv)
{
	unsigned char data[8];
	int fd, unit, changed = 0;
	if (argc < 3 || (strcmp(argv[2], "get") && strcmp(argv[2], "set")))
		return usage();
	unit = extension_unit(argv[1]);
	if (unit < 0) {
		fprintf(stderr, "PiSight extension unit not found for %s\n", argv[1]);
		return 1;
	}
	fd = open(argv[1], O_RDWR | O_CLOEXEC);
	if (fd < 0) { perror(argv[1]); return 1; }
	if (query(fd, unit, UVC_GET_CUR, data) < 0) {
		perror("UVC GET_CUR"); close(fd); return 1;
	}
	if (data[0] != 1 || data[1] < 25 || data[1] > 75 ||
	    data[4] > 2 || data[5] > 1) {
		fputs("Unsupported PiSight settings payload\n", stderr);
		close(fd); return 1;
	}
	if (!strcmp(argv[2], "get")) {
		if (argc != 3) { close(fd); return usage(); }
		print_settings(data);
		close(fd); return 0;
	}
	for (int i = 3; i < argc; i += 2) {
		char *end;
		if (i + 1 == argc) { close(fd); return usage(); }
		if (!strcmp(argv[i], "--fov")) {
			long value = strtol(argv[i + 1], &end, 10);
			if (*end || value < 25 || value > 75) { close(fd); return usage(); }
			data[1] = value;
		} else if (!strcmp(argv[i], "--ev")) {
			double value = strtod(argv[i + 1], &end);
			if (end == argv[i + 1] || *end || !isfinite(value) || value < -2.0 || value > 2.0) {
				close(fd); return usage();
			}
			int tenths = (int)lround(value * 10.0);
			if (fabs(value * 10.0 - tenths) > 0.00001) { close(fd); return usage(); }
			data[2] = tenths & 0xff;
			data[3] = (tenths >> 8) & 0xff;
		} else if (!strcmp(argv[i], "--logo")) {
			if (!strcmp(argv[i + 1], "off")) data[4] = 0;
			else if (!strcmp(argv[i + 1], "on")) data[4] = 1;
			else if (!strcmp(argv[i + 1], "activity")) data[4] = 2;
			else { close(fd); return usage(); }
		} else if (!strcmp(argv[i], "--mic")) {
			if (!strcmp(argv[i + 1], "off")) data[5] = 0;
			else if (!strcmp(argv[i + 1], "on")) data[5] = 1;
			else { close(fd); return usage(); }
		} else { close(fd); return usage(); }
		changed = 1;
	}
	if (!changed) { close(fd); return usage(); }
	if (query(fd, unit, UVC_SET_CUR, data) < 0) {
		perror("UVC SET_CUR"); close(fd); return 1;
	}
	unsigned char verify[8];
	if (query(fd, unit, UVC_GET_CUR, verify) < 0 || memcmp(data, verify, sizeof data)) {
		fputs("Settings were not confirmed by PiSight; check the camera log and boot partition\n", stderr);
		close(fd); return 1;
	}
	print_settings(verify);
	fputs("FOV and EV apply to the live camera; power-cycle PiSight for logo and microphone changes.\n", stderr);
	close(fd);
	return 0;
}
