#include <mgba/flags.h>
#include <mgba/core/core.h>
#include <mgba/core/log.h>
#include <mgba/core/cheats.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

static void quiet(struct mLogger* l, int c, enum mLogLevel lv, const char* f, va_list a) { (void) l; (void) c; (void) lv; (void) f; (void) a; }
static struct mLogger logger = { .log = quiet };
static struct mCore* core;
static color_t buf[256 * 256];

static int px(void) { return (int16_t) core->rawRead16(core, 0x02025734, -1); }
static int py(void) { return (int16_t) core->rawRead16(core, 0x02025736, -1); }
static void frames(int keys, int n) { core->setKeys(core, keys); for (int i = 0; i < n; ++i) core->runFrame(core); }
static void where(const char* tag) {
	printf("%-14s map %d.%d pos (%d,%d)\n", tag, (int8_t) core->rawRead8(core, 0x02025738, -1), (int8_t) core->rawRead8(core, 0x02025739, -1), px(), py());
}

/* usage: drive rom save out.raw CMD...   CMD = U3 / D2 / L11 / R4 (walk tiles), B, A, W60 (wait frames), P (print) */
int main(int argc, char** argv) {
	mLogSetDefaultLogger(&logger);
	core = mCoreFind(argv[1]);
	core->init(core);
	core->setVideoBuffer(core, buf, 256);
	mCoreInitConfig(core, NULL);
	mCoreLoadFile(core, argv[1]);
	mCoreLoadSaveFile(core, argv[2], getenv("WRITESAVE") == NULL);
	core->reset(core);
	if (getenv("CHEAT")) {  /* e.g. CHEAT="3B0C8C5E 96FB832D" */
		struct mCheatDevice* dev = core->cheatDevice(core);
		struct mCheatSet* set = dev->createSet(dev, NULL);
		mCheatAddSet(dev, set);
		static char code[8192];
		strncpy(code, getenv("CHEAT"), sizeof(code) - 1);
		for (char* line = strtok(code, "+"); line; line = strtok(NULL, "+"))
			if (!mCheatAddLine(set, line, 0)) printf("REJECTED %s\n", line);
	}
	int boot[][2] = { {0, 600}, {8, 5}, {0, 120}, {1, 5}, {0, 120}, {1, 5}, {0, 240}, {1, 5}, {0, 600} };
	for (unsigned s = 0; s < sizeof(boot) / sizeof(*boot); ++s) frames(boot[s][0], boot[s][1]);
	where("start");
	for (int a = 4; a < argc; ++a) {
		char c = argv[a][0]; int n = atoi(argv[a] + 1);
		int key = c == 'U' ? 64 : c == 'D' ? 128 : c == 'L' ? 32 : c == 'R' ? 16 : 0;
		if (key) {
			for (int t = 0; t < n; ++t) {
				int x0 = px(), y0 = py(), f = 0;
				core->setKeys(core, key);
				while (px() == x0 && py() == y0 && f < 60) { core->runFrame(core); ++f; }
				frames(key, 2);
			}
			frames(0, 20);
			where(argv[a]);
		} else if (c == 'B') { frames(2, 4); frames(0, 60); }
		else if (c == 'A') { frames(1, 4); frames(0, 60); }
		else if (c == 'W') { frames(0, n); }
		else if (c == 'P') { where("now"); }
		else if (c == 'X') {  /* screenshot to <out>.<n>.raw */
			static int shot = 0;
			char name[512]; snprintf(name, sizeof(name), "%s.%d.raw", argv[3], shot++);
			FILE* f = fopen(name, "wb");
			for (int y = 0; y < 160; ++y) fwrite(&buf[y * 256], sizeof(color_t), 240, f);
			fclose(f);
		}
		else if (c == 'K') { frames(n, 4); frames(0, 40); }  /* raw key mask */
		else if (c == 'T') {  /* T<flag hex>: print a SaveBlock1 flag */
			int flag = strtol(argv[a] + 1, NULL, 16);
			printf("flag %#x = %d\n", flag, (core->rawRead8(core, 0x02025734 + 0x1220 + flag / 8, -1) >> (flag % 8)) & 1);
		}
	}
	FILE* out = fopen(argv[3], "wb");
	for (int y = 0; y < 160; ++y) fwrite(&buf[y * 256], sizeof(color_t), 240, out);
	fclose(out);
	core->deinit(core);  /* flushes the save file when WRITESAVE is set */
	return 0;
}
