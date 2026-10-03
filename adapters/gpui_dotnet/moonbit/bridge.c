#include "bridge.h"
#include <pthread.h>
#include <stdio.h>
#include <string.h>

const GpuiDotnetApiV1 *moon_api;
static MoonRender moon_render;
static MoonClick moon_click;
static MoonStarted moon_started;
static int claimed;
static int callback_depth;

static int32_t render(uint64_t session, RenderArena *arena, uint32_t *root) {
    if (!pthread_main_np() || callback_depth || session != 1 || !arena || !root) return -2002;
    arena->node_length = arena->op_length = arena->child_length = arena->utf8_length = 0;
    arena->required_node_capacity = arena->required_op_capacity = 0;
    arena->required_child_capacity = arena->required_utf8_capacity = 0;
    MoonFrame frame = {.arena = arena, .root = root};
    callback_depth = 1;
    int32_t status = moon_render(&frame);
    callback_depth = 0;
    if (!status) status = moon_api->validate_render(arena, *root);
    if (!status) {
        fprintf(stderr, "[moon-mobile] rendered: %.*s\n", arena->utf8_length, arena->utf8);
    }
    return status;
}

static int32_t click(uint64_t session, uint64_t token, uint64_t payload, const NativeClickEvent *event) {
    if (!pthread_main_np() || callback_depth || session != 1 || !event || payload || !token || token > INT32_MAX) return -2002;
    callback_depth = 1;
    int32_t status = moon_click((int32_t)token - 1);
    callback_depth = 0;
    fprintf(stderr, "[moon-mobile] click token=%llu status=%d\n", (unsigned long long)token, status);
    return status;
}

static int32_t started(uint64_t application) { return application == 1 ? moon_started() : -2002; }
static int32_t range(uint64_t s, uint64_t t, uint32_t a, uint32_t b, RenderArena *r, uint32_t *o) {
    (void)s; (void)t; (void)a; (void)b; (void)r; (void)o; return -2003;
}
static int32_t control(uint64_t s, uint64_t t, const NativeControlEvent *e) { (void)s; (void)t; (void)e; return -2003; }
static int32_t closed(uint64_t a, uint64_t s, int32_t v) { (void)a; (void)s; return v; }
static int32_t menu(uint64_t a, uint64_t t) { (void)a; (void)t; return -2003; }
static int32_t dynamic(uint64_t s, uint32_t o) { (void)s; (void)o; return -2003; }

int32_t gpui_moon_host_start(MoonRender render_fn, MoonClick click_fn, MoonStarted started_fn) {
    if (!pthread_main_np() || claimed || !render_fn || !click_fn || !started_fn) return -2001;
    const GpuiDotnetApiV1 *api = gpui_dotnet_get_api(GPUI_NATIVE_ABI_VERSION);
    if (!api || api->struct_size < sizeof(*api) || api->abi_version != GPUI_NATIVE_ABI_VERSION) return -2010;
    if (api->schema_hash != GPUI_SCHEMA_HASH) return -2011;
    if (!api->validate_render || !api->run_application || !api->notify_view ||
        !api->dispatch_command || !api->dispatch_application_command || !api->dispatch_application_menu) return -2010;
    moon_api = api;
    moon_render = render_fn;
    moon_click = click_fn;
    moon_started = started_fn;
    claimed = 1;
    ManagedCallbacks callbacks = {0};
    callbacks.struct_size = sizeof(callbacks);
    callbacks.render = render;
    callbacks.click = click;
    callbacks.list_render_range = range;
    callbacks.control_event = control;
    callbacks.application_started = started;
    callbacks.window_closed = closed;
    callbacks.menu_action = menu;
    callbacks.dynamic_frame = dynamic;
    // Embedded startup returns immediately. Callback functions and MoonBit roots live
    // for the process lifetime; do not clear them after run_application returns.
    return api->run_application(1, &callbacks);
}
