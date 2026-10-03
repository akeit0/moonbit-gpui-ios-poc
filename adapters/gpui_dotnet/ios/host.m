#include "mobile_host.h"
#include <stdbool.h>

extern int32_t gpui_moonbit_start(void);
extern void gpui_ios_set_embedded(void);
extern void *gpui_ios_get_window(void);
extern void *gpui_ios_view_controller(void *window);
extern void gpui_ios_layout_view(void *window);
extern bool gpui_ios_request_frame(void *window);
extern void gpui_ios_did_become_active(void *application);
extern void gpui_ios_will_resign_active(void *application);
extern void gpui_ios_did_enter_background(void *application);

static void *window;

void mobile_host_prepare(void) { gpui_ios_set_embedded(); }
int32_t mobile_host_start(void) { return gpui_moonbit_start(); }
UIViewController *mobile_host_view_controller(void) {
    window = gpui_ios_get_window();
    return (__bridge UIViewController *)gpui_ios_view_controller(window);
}
UIColor *mobile_host_background_color(void) {
    return [UIColor colorWithRed:15.0/255 green:23.0/255 blue:42.0/255 alpha:1];
}
void mobile_host_layout(void) { gpui_ios_layout_view(window); }
void mobile_host_request_frame(void) { gpui_ios_request_frame(window); }
void mobile_host_did_become_active(void) { gpui_ios_did_become_active(NULL); }
void mobile_host_will_resign_active(void) { gpui_ios_will_resign_active(NULL); }
void mobile_host_did_enter_background(void) { gpui_ios_did_enter_background(NULL); }
