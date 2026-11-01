#include <mgba/flags.h>
#include <mgba/core/core.h>
#include <mgba/core/log.h>
#include <stdio.h>

static void quiet(struct mLogger* l, int c, enum mLogLevel lv, const char* f, va_list a) { (void) l; (void) c; (void) lv; (void) f; (void) a; }
static struct mLogger logger = { .log = quiet };

/* Boot the ROM with a save, press through the title screen to CONTINUE, then dump gPlayerParty. */
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
	/* key, frames held */
	int script[][2] = { {0, 600}, {8, 5}, {0, 120}, {1, 5}, {0, 120}, {1, 5}, {0, 240}, {1, 5}, {0, 300} };
	for (unsigned s = 0; s < sizeof(script) / sizeof(*script); ++s) {
		core->setKeys(core, script[s][0]);
		for (int f = 0; f < script[s][1]; ++f) core->runFrame(core);
	}
	FILE* out = fopen(argv[3], "wb");
	for (uint32_t a = 0x03004350; a < 0x03004360 + 600; ++a) fputc(core->rawRead8(core, a, -1), out);
	fclose(out);
	return 0;
}
