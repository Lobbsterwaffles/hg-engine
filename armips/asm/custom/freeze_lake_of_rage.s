.nds
.thumb

// Freeze Lake of Rage to always show the non-Wednesday (flooded) map
// 
// The function ShouldUseAlternateLakeOfRage at 0x203b114 controls whether
// the Lake of Rage shows the lowered water level (Wednesday) or normal level.
// 
// Original behavior:
//   Returns TRUE (1) if:
//     - FLAG_RED_GYARADOS_MEET is set (player battled Red Gyarados)
//     - Player is on Route 43 or Lake of Rage
//     - It's Wednesday
//   Returns FALSE (0) otherwise
//
// This patch makes it ALWAYS return FALSE, so the lake is always flooded
// (the normal, non-Wednesday appearance).
//
// Original bytes at 0x203b114: 38 B5 84 B0 (PUSH {r3,r4,r5,lr}; SUB sp, #0x10)
// Patched to: 00 20 70 47 (MOV r0, #0; BX lr) - immediately return 0

.open "base/arm9.bin", 0x02000000

.org 0x0203B114
    mov r0, #0      // Return FALSE (normal flooded map)
    bx lr           // Return immediately

.close
