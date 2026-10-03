#include "bridge.h"
#include <assert.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

extern void moonbit_init(void);
extern int32_t gpui_moonbit_start(void);

static ManagedCallbacks saved;
static int mode, notified, clicked;

static int32_t validate(const RenderArena *a, uint32_t root) {
    assert(root < (uint32_t)a->node_length);
    assert(a->node_length <= a->node_capacity && a->op_length <= a->op_capacity);
    assert(a->child_length <= a->child_capacity && a->utf8_length <= a->utf8_capacity);
    int found = 0;
    const char *expected = clicked ? "Count: 1" : "Count: 0";
    for (int32_t i = 0; i < a->node_length; ++i) {
        const NodeRecord *n = &a->nodes[i];
        assert((uint64_t)n->data_offset + n->data_length <= (uint32_t)a->utf8_length);
        if (n->component == GPUI_COMPONENT_TEXT && n->data_length == strlen(expected) &&
            !memcmp(a->utf8 + n->data_offset, expected, n->data_length)) found = 1;
    }
    assert(found);
    return 0;
}
static int32_t run(uint64_t app, const ManagedCallbacks *callbacks) {
    assert(app == 1 && callbacks->struct_size == sizeof(*callbacks));
    saved = *callbacks;
    assert(saved.application_started(1) == 0);
    return 0;
}
static int32_t notify(uint64_t window) { assert(window == 1); ++notified; return 0; }
static int32_t command(uint64_t window, const NativeResourceCommand *value) { (void)window; (void)value; return 0; }
static int32_t open_window(uint64_t app, const NativeApplicationCommand *value) {
    assert(app == 1 && value->window_id == 1 && value->command == 1);
    assert(value->reserved == 0 && value->reserved2 == 0 && value->title_length > 0);
    assert(value->width == 390 && value->height == 844);
    return 0;
}
static int32_t menu(uint64_t app, const NativeMenuCommand *value) { (void)app; (void)value; return 0; }

const GpuiDotnetApiV1 *gpui_dotnet_get_api(uint32_t version) {
    static GpuiDotnetApiV1 api;
    assert(version == GPUI_NATIVE_ABI_VERSION);
    api = (GpuiDotnetApiV1){sizeof(api), GPUI_NATIVE_ABI_VERSION, GPUI_SCHEMA_HASH,
                           validate, run, notify, command, open_window, menu};
    switch (mode) {
        case 1: return NULL;
        case 2: api.struct_size = 16; break;
        case 3: api.abi_version = 8; break;
        case 4: api.schema_hash ^= 1; break;
        case 5: api.dispatch_command = NULL; break;
    }
    return &api;
}

static void *worker(void *arg) {
    (void)arg;
    NativeClickEvent event = {0};
    assert(saved.click(1, 1, 0, &event) == -2002);
    assert(gpui_moon_host_invalidate() == -2001);
    return NULL;
}

int main(int argc, char **argv) {
    assert(argc == 2);
    mode = atoi(argv[1]);
    moonbit_init();
    int32_t status = gpui_moonbit_start();
    if (mode) {
        assert(status == (mode == 4 ? -2011 : -2010));
        puts("ABI mismatch rejected");
        return 0;
    }
    assert(status == 0);
    // These callbacks occur after embedded startup returned; MoonBit roots stay alive.
    RenderArena a = {0};
    uint32_t root = 0;
    assert(saved.render(1, &a, &root) == 1);
    assert(a.required_node_capacity > 0 && a.required_op_capacity > 0);
    assert(a.required_child_capacity > 0 && a.required_utf8_capacity > 0);
    a.node_capacity = a.required_node_capacity;
    a.op_capacity = a.required_op_capacity;
    a.child_capacity = a.required_child_capacity;
    a.utf8_capacity = a.required_utf8_capacity;
    a.nodes = calloc((size_t)a.node_capacity, sizeof(*a.nodes));
    a.ops = calloc((size_t)a.op_capacity, sizeof(*a.ops));
    a.children = calloc((size_t)a.child_capacity, sizeof(*a.children));
    a.utf8 = calloc((size_t)a.utf8_capacity, 1);
    assert(a.nodes && a.ops && a.children && a.utf8);
    assert(saved.render(1, &a, &root) == 0);
    NativeClickEvent event = {0};
    assert(saved.click(1, 0, 0, &event) == -2002);
    assert(saved.click(1, 99, 0, &event) == -2002);
    assert(saved.click(1, 1, 0, &event) == 0);
    clicked = 1;
    assert(notified == 1);
    assert(saved.render(1, &a, &root) == 0);
    assert(gpui_moonbit_start() == -2001);
    pthread_t thread;
    assert(pthread_create(&thread, NULL, worker, NULL) == 0);
    assert(pthread_join(thread, NULL) == 0);
    MoonFrame frame = {.arena = &a, .root = &root};
    assert(gpui_moon_frame_node(&frame, 2, NULL, 1) == -1);
    assert(gpui_moon_frame_finish(&frame, 0) == -2004);
    free(a.nodes); free(a.ops); free(a.children); free(a.utf8);
    puts("MoonBit state, embedded lifetime, arena growth and thread checks passed");
    return 0;
}
