#include "bridge.h"
#include <limits.h>
#include <string.h>

static int reserve(MoonFrame *frame, int32_t current, int32_t count, int32_t capacity, int32_t *required) {
    if (current < 0 || count < 0 || capacity < 0 || current > INT32_MAX - count) {
        frame->status = -2004;
        return 0;
    }
    if (current + count > capacity) {
        *required = current + count;
        if (frame->status >= 0) frame->status = 1;
        return 0;
    }
    return 1;
}

int32_t gpui_moon_frame_node(MoonFrame *frame, int32_t component, const uint8_t *text, int32_t length) {
    if (!frame) return -1;
    if (!frame->arena || length < 0 || (length && !text) ||
        (component != GPUI_COMPONENT_DIV && component != GPUI_COMPONENT_TEXT && component != GPUI_COMPONENT_BUTTON)) {
        frame->status = -2004; return -1;
    }
    RenderArena *a = frame->arena;
    if (frame->status < 0) return -1;
    int nodes_fit = reserve(frame, frame->nodes, 1, a->node_capacity, &a->required_node_capacity);
    int bytes_fit = reserve(frame, frame->utf8, length, a->utf8_capacity, &a->required_utf8_capacity);
    if (frame->status < 0) return -1;
    int32_t id = frame->nodes++;
    int32_t offset = frame->utf8;
    frame->utf8 += length;
    if (nodes_fit && bytes_fit) {
        if (!a->nodes || (length && !a->utf8)) { frame->status = -2004; return -1; }
        a->nodes[id] = (NodeRecord){(uint16_t)component, 0, (uint32_t)offset, (uint32_t)length};
        if (length) memcpy(a->utf8 + offset, text, (size_t)length);
    }
    return id;
}

void gpui_moon_frame_op(MoonFrame *frame, int32_t node, int32_t code, int32_t kind, uint64_t value) {
    if (!frame || frame->status < 0) return;
    RenderArena *a = frame->arena;
    if (node < 0 || node >= frame->nodes || code < 0 || code > UINT16_MAX || kind < 0 || kind > 5) {
        frame->status = -2004; return;
    }
    int fits = reserve(frame, frame->ops, 1, a->op_capacity, &a->required_op_capacity);
    if (frame->status < 0) return;
    int32_t index = frame->ops++;
    if (!fits) return;
    if (!a->ops) { frame->status = -2004; return; }
    a->ops[index] = (OpRecord){(uint32_t)node, (uint16_t)code, (uint16_t)kind, value, 0};
}

void gpui_moon_frame_child(MoonFrame *frame, int32_t parent, int32_t child) {
    if (!frame || frame->status < 0) return;
    RenderArena *a = frame->arena;
    if (parent < 0 || child < 0 || parent >= frame->nodes || child >= frame->nodes || parent == child) {
        frame->status = -2004; return;
    }
    int fits = reserve(frame, frame->children, 1, a->child_capacity, &a->required_child_capacity);
    if (frame->status < 0) return;
    int32_t index = frame->children++;
    if (!fits) return;
    if (!a->children) { frame->status = -2004; return; }
    a->children[index] = (ChildRecord){(uint32_t)parent, (uint32_t)child};
}

int32_t gpui_moon_frame_finish(MoonFrame *frame, int32_t root) {
    if (!frame || !frame->arena || !frame->root) return -2004;
    if (frame->status) return frame->status;
    if (root < 0 || root >= frame->nodes) return -2004;
    frame->arena->node_length = frame->nodes;
    frame->arena->op_length = frame->ops;
    frame->arena->child_length = frame->children;
    frame->arena->utf8_length = frame->utf8;
    *frame->root = (uint32_t)root;
    return 0;
}

uint64_t gpui_moon_float_bits(float value) {
    uint32_t bits;
    memcpy(&bits, &value, sizeof(bits));
    return bits;
}
