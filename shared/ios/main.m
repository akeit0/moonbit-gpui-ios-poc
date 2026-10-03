#import <UIKit/UIKit.h>
#import <QuartzCore/QuartzCore.h>
#include "mobile_host.h"

extern void moonbit_init(void);

@interface MoonMobileHost : UIViewController
@property(nonatomic, strong) UIViewController *content;
@end

@implementation MoonMobileHost
- (void)viewDidLoad {
    [super viewDidLoad];
    self.view.backgroundColor = mobile_host_background_color();
    [self addChildViewController:self.content];
    [self.view addSubview:self.content.view];
    [self.content didMoveToParentViewController:self];
}
- (void)viewDidLayoutSubviews {
    [super viewDidLayoutSubviews];
    self.content.view.frame = self.view.safeAreaLayoutGuide.layoutFrame;
    mobile_host_layout();
    mobile_host_request_frame();
}
@end

@interface SceneDelegate : UIResponder <UIWindowSceneDelegate>
@property(nonatomic, strong) UIWindow *window;
@property(nonatomic, strong) CADisplayLink *displayLink;
@end

@implementation SceneDelegate
- (void)scene:(UIScene *)scene willConnectToSession:(UISceneSession *)session options:(UISceneConnectionOptions *)options {
    (void)session; (void)options;
    if (![scene isKindOfClass:[UIWindowScene class]]) return;
    UIViewController *content = mobile_host_view_controller();
    if (!content) {
        NSLog(@"MoonBit renderer startup did not produce a view controller");
        abort();
    }
    MoonMobileHost *host = [MoonMobileHost new];
    host.content = content;
    self.window = [[UIWindow alloc] initWithWindowScene:(UIWindowScene *)scene];
    self.window.rootViewController = host;
    [self.window makeKeyAndVisible];
    self.displayLink = [CADisplayLink displayLinkWithTarget:self selector:@selector(requestFrame:)];
    [self.displayLink addToRunLoop:NSRunLoop.mainRunLoop forMode:NSRunLoopCommonModes];
}
- (void)requestFrame:(CADisplayLink *)sender { (void)sender; mobile_host_request_frame(); }
- (void)sceneDidBecomeActive:(UIScene *)scene { (void)scene; mobile_host_did_become_active(); }
- (void)sceneWillResignActive:(UIScene *)scene { (void)scene; mobile_host_will_resign_active(); }
- (void)sceneDidEnterBackground:(UIScene *)scene { (void)scene; mobile_host_did_enter_background(); }
- (void)sceneDidDisconnect:(UIScene *)scene {
    (void)scene;
    [self.displayLink invalidate];
    self.displayLink = nil;
}
@end

@interface AppDelegate : UIResponder <UIApplicationDelegate>
@end

@implementation AppDelegate
- (BOOL)application:(UIApplication *)application didFinishLaunchingWithOptions:(NSDictionary *)options {
    (void)application; (void)options;
    mobile_host_prepare();
    moonbit_init();
    int32_t status = mobile_host_start();
    NSLog(@"MoonBit embedded startup status=%d", status);
    if (status != 0) abort();
    return YES;
}
@end

int main(int argc, char *argv[]) {
    @autoreleasepool {
        return UIApplicationMain(argc, argv, nil, NSStringFromClass(AppDelegate.class));
    }
}
