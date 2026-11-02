@ Replaces the "else" branch of CB2_EndTrainerBattle (jumped to with bx, so the caller's
@ pushed lr is still on the stack). If the player ran, the trainer is not marked as beaten,
@ stops spotting the player until the map reloads, and its script ends with releaseall.
	.syntax unified
	.thumb
	.global far_entry
far_entry:
	ldr r0, =0x080546D5          @ CB2_ReturnToFieldContinueScriptPlayMapMusic
	ldr r3, =0x080003CD          @ SetMainCallback2
	bl via_r3
	ldr r0, =0x02024D26          @ gBattleOutcome
	ldrb r0, [r0]
	cmp r0, #4                   @ B_OUTCOME_RAN
	beq ran
	ldr r3, =0x0808257D          @ SetCurrentTrainerBattledFlag
	bl via_r3
	b done
ran:
	ldr r0, =0x03004AE0          @ gSelectedObjectEvent
	ldrb r0, [r0]
	movs r1, #0x24
	muls r0, r1
	ldr r1, =0x030048A0          @ gObjectEvents
	adds r0, r0, r1
	movs r1, #0
	strb r1, [r0, #7]            @ trainerType = TRAINER_TYPE_NONE (no line of sight)
	ldr r0, =0x0815B594          @ "releaseall; end"
	ldr r3, =0x080655B9          @ ScriptContext1_SetupScript
	bl via_r3
done:
	pop {r0}
	bx r0
via_r3:
	bx r3
	.pool
