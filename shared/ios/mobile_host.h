#pragma once
#import <UIKit/UIKit.h>
#include <stdint.h>

// Single-window renderer boundary. Implemented by the selected native adapter.
// UIKit calls these on the main thread; startup must return for embedded hosting.
void mobile_host_prepare(void);
int32_t mobile_host_start(void);
UIViewController *mobile_host_view_controller(void);
UIColor *mobile_host_background_color(void);
void mobile_host_layout(void);
void mobile_host_request_frame(void);
void mobile_host_did_become_active(void);
void mobile_host_will_resign_active(void);
void mobile_host_did_enter_background(void);
