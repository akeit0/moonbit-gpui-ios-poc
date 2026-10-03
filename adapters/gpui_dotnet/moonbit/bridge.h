#pragma once
#include "gpui_native.g.h"
#include <stddef.h>

typedef struct MoonFrame {
    RenderArena *arena;
    uint32_t *root;
    int32_t status;
    int32_t nodes, ops, children, utf8;
} MoonFrame;

typedef int32_t (*MoonRender)(MoonFrame *);
typedef int32_t (*MoonClick)(int32_t);
typedef int32_t (*MoonStarted)(void);

extern const GpuiDotnetApiV1 *gpui_dotnet_get_api(uint32_t);
extern const GpuiDotnetApiV1 *moon_api;
int32_t gpui_moon_frame_finish(MoonFrame *, int32_t);
int32_t gpui_moon_frame_node(MoonFrame *, int32_t, const uint8_t *, int32_t);
void gpui_moon_frame_op(MoonFrame *, int32_t, int32_t, int32_t, uint64_t);
void gpui_moon_frame_child(MoonFrame *, int32_t, int32_t);
int32_t gpui_moon_host_start(MoonRender, MoonClick, MoonStarted);
int32_t gpui_moon_host_open(const uint8_t *, int32_t);
int32_t gpui_moon_host_invalidate(void);
