#include <mgba/flags.h>
#include <mgba/core/core.h>
#include <mgba/core/cheats.h>
#include <mgba/core/log.h>
#include <mgba/internal/arm/arm.h>
#include <mgba/internal/arm/isa-inlines.h>
#include <stdio.h>
#include <string.h>

static void quiet(struct mLogger* l, int c, enum mLogLevel lv, const char* f, va_list a) { (void) l; (void) c; (void) lv; (void) f; (void) a; }
static struct mLogger logger = { .log = quiet };
#define LOOP 0x02030200u

/* Call IsHMMove2 / IsHMMove on a few moves, optionally with a cheat code (argv[2], '+'-separated lines). */
int main(int argc, char** argv) {
	mLogSetDefaultLogger(&logger);
	struct mCore* core = mCoreFind(argv[1]);
	core->init(core);
	static color_t buf[256 * 256];
	core->setVideoBuffer(core, buf, 256);
	mCoreInitConfig(core, NULL);
	mCoreLoadFile(core, argv[1]);
	core->reset(core);
	if (argc > 2) {
		struct mCheatDevice* dev = core->cheatDevice(core);
		struct mCheatSet* set = dev->createSet(dev, NULL);
		mCheatAddSet(dev, set);
		char code[1024]; strncpy(code, argv[2], sizeof(code) - 1);
		for (char* line = strtok(code, "+"); line; line = strtok(NULL, "+"))
			if (!mCheatAddLine(set, line, 0)) printf("REJECTED %s\n", line);
	}
	for (int f = 0; f < 300; ++f) core->runFrame(core);
	core->rawWrite16(core, 0x04000208, -1, 0);
	struct ARMCore* cpu = core->cpu;
	uint32_t funcs[] = { 0x08040A00, 0x0806F7B8, 0x08040A00 };
	const char* names[] = { "warmup", "IsHMMove2 (level-up/evolution)", "IsHMMove (TM forget screen)" };
	uint32_t fn2[] = { 0x08040A00, 0x08040A00, 0x0806F7B8 };
	int moves[] = { 57, 70, 15, 33 };
	const char* mnames[] = { "SURF", "STRENGTH", "CUT", "TACKLE" };
	for (int k = 0; k < 3; ++k) {
		if (k) printf("%s:", names[k]);
		for (int m = 0; m < 4; ++m) {
			core->rawWrite16(core, LOOP, -1, 0xE7FE);
			cpu->gprs[0] = moves[m]; cpu->gprs[ARM_SP] = 0x03007C00; cpu->gprs[ARM_LR] = LOOP | 1;
			cpu->cpsr.t = 1; cpu->executionMode = MODE_THUMB;
			cpu->gprs[ARM_PC] = fn2[k]; ThumbWritePC(cpu);
			for (int s = 0; s < 5000; ++s) {
				ARMRun(cpu);
				if ((cpu->gprs[ARM_PC] & ~3u) - 4 <= LOOP && (cpu->gprs[ARM_PC] & ~3u) >= LOOP) break;
			}
			if (k) printf(" %s=%d", mnames[m], cpu->gprs[0] & 0xFF);
		}
		if (k) printf("\n");
	}
	(void) funcs;
	return 0;
}
