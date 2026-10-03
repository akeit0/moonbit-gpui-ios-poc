/// UIKit calls this stable C export after moonbit_init().
#export_name("gpui_moonbit_start")
pub fn gpui_moonbit_start() -> Int {
  let count : Ref[Int] = { val: 0 }
  let app = App::new("MoonBit + GPUI on iOS", fn(ui) {
    ui.div().v_stack().gap_px(18.0).padding_px(28.0).grow()
      .width_percent(100.0).height_percent(100.0)
      .background(0x0f172affU).text_color(0xf1f5f9ffU)
      .child(ui.text("MoonBit + GPUI").font_size_px(28.0))
      .child(ui.text("MoonBit state, rendered through Metal."))
      .child(ui.text("Count: \{count.val}").font_size_px(22.0))
      .child(ui.button("increment", "Tap me").on_click(fn() {
        count.val = count.val + 1
        invalidate()
      }))
  })
  app.start_embedded()
}
