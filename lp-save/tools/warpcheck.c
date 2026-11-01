#include <mgba/flags.h>
#include <mgba/core/core.h>
#include <mgba/core/log.h>
#include <stdio.h>

static void quiet(struct mLogger* l, int c, enum mLogLevel lv, const char* f, va_list a) { (void) l; (void) c; (void) lv; (void) f; (void) a; }
static struct mLogger logger = { .log = quiet };

/* Boot with a save, choose CONTINUE, then print the player's map/position and save a screenshot (raw RGBX 240x160). */
int main(int argc, char** argv) {
	mLogSetDefaultLogger(&logger);
	struct mCore* core = mCoreFind(argv[1]);
	core->init(core);
	static color_t buf[256 * 256];
	core->setVideoBuffer(core, buf, 256);
	mCoreInitConfig(core, NULL);
	mCoreLoadFile(core, argv[1]);
	mCoreLoadSaveFile(core, argv[2], true);
	core->reset(core);
	int script[][2] = { {0, 600}, {8, 5}, {0, 120}, {1, 5}, {0, 120}, {1, 5}, {0, 240}, {1, 5}, {0, 600} };
	for (unsigned s = 0; s < sizeof(script) / sizeof(*script); ++s) {
		core->setKeys(core, script[s][0]);
		for (int f = 0; f < script[s][1]; ++f) core->runFrame(core);
	}
	printf("map %d.%d pos (%d,%d)\n", (int8_t) core->rawRead8(core, 0x02025738, -1), (int8_t) core->rawRead8(core, 0x02025739, -1),
	       (int16_t) core->rawRead16(core, 0x02025734, -1), (int16_t) core->rawRead16(core, 0x02025736, -1));
	/* try walking: right, down, left, up (GBA keys: R=16, L=32, U=64, D=128) */
	int dirs[] = { 16, 128, 32, 64 };
	const char* names[] = { "right", "down", "left", "up" };
	for (int d = 0; d < 4; ++d) {
		core->setKeys(core, dirs[d]);
		for (int f = 0; f < 40; ++f) core->runFrame(core);
		core->setKeys(core, 0);
		for (int f = 0; f < 20; ++f) core->runFrame(core);
		printf("after %s: pos (%d,%d)\n", names[d], (int16_t) core->rawRead16(core, 0x02025734, -1), (int16_t) core->rawRead16(core, 0x02025736, -1));
	}
	FILE* out = fopen(argv[3], "wb");
	for (int y = 0; y < 160; ++y) fwrite(&buf[y * 256], sizeof(color_t), 240, out);
	fclose(out);
	return 0;
}
