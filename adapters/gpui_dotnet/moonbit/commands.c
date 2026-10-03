#include "bridge.h"
#include <pthread.h>
#include <string.h>

int32_t gpui_moon_host_open(const uint8_t *title, int32_t length) {
    if (!pthread_main_np() || !moon_api || !title || length <= 0 || memchr(title, 0, (size_t)length)) return -2002;
    NativeApplicationCommand command = {0};
    command.window_id = 1;
    command.command = 1;
    command.flags = 2 | (2 << 2); // Activate, hidden system title bar.
    command.title = title;
    command.title_length = length;
    command.width = 390;
    command.height = 844;
    return moon_api->dispatch_application_command(1, &command);
}

int32_t gpui_moon_host_invalidate(void) {
    return pthread_main_np() && moon_api ? moon_api->notify_view(1) : -2001;
}
