/// An intentionally small semantic frontend for the mobile host's ABI 1.
pub struct App {
  title : String
  render : (Frame) -> Element
  handlers : Ref[Array[() -> Int]]
}

pub struct Frame {
  handle : FrameHandle
  handlers : Array[() -> Int]
}

pub struct Element {
  frame : Frame
  id : Int
}

let active_app : Ref[App?] = { val: None }

pub fn App::new(title : String, render : (Frame) -> Element) -> App {
  { title, render, handlers: { val: [] } }
}

pub fn App::start_embedded(self : App) -> Int {
  if active_app.val is Some(_) { return -2001 }
  active_app.val = Some(self)
  host_start(fn(frame) { render_callback(frame) }, fn(index) { click_callback(index) }, fn() { started_callback() })
}

pub fn invalidate() -> Int {
  host_invalidate()
}

fn started_callback() -> Int {
  match active_app.val {
    None => -2001
    Some(app) => {
      let title = @utf8.encode(app.title)
      host_open(title, title.length())
    }
  }
}

fn render_callback(handle : FrameHandle) -> Int {
  match active_app.val {
    None => -2001
    Some(app) => {
      let frame : Frame = { handle, handlers: [] }
      let root = (app.render)(frame)
      let status = frame_finish(handle, root.id)
      // Arena-growth retries must not retire callbacks from the committed frame.
      if status == 0 { app.handlers.val = frame.handlers }
      status
    }
  }
}

fn click_callback(index : Int) -> Int {
  match active_app.val {
    Some(app) if index >= 0 && index < app.handlers.val.length() =>
      (app.handlers.val[index])()
    _ => -2002
  }
}

fn Frame::node(self : Frame, kind : Int, text : String) -> Element {
  let bytes = @utf8.encode(text)
  { frame: self, id: frame_node(self.handle, kind, bytes, bytes.length()) }
}

pub fn Frame::div(self : Frame) -> Element { self.node(COMPONENT_DIV, "") }
pub fn Frame::text(self : Frame, text : String) -> Element { self.node(COMPONENT_TEXT, text) }
pub fn Frame::button(self : Frame, key : String, text : String) -> Element {
  self.node(COMPONENT_BUTTON, key).child(self.text(text)).padding_px(12.0)
}

fn Element::op(self : Element, code : Int, kind : Int, value : UInt64) -> Element {
  frame_op(self.frame.handle, self.id, code, kind, value)
  self
}

pub fn Element::v_stack(self : Element) -> Element { self.op(OP_V_STACK, 0, 0UL) }
pub fn Element::gap_px(self : Element, value : Float) -> Element { self.op(OP_GAP_PX, 1, float_bits(value)) }
pub fn Element::padding_px(self : Element, value : Float) -> Element { self.op(OP_PADDING_PX, 1, float_bits(value)) }
pub fn Element::font_size_px(self : Element, value : Float) -> Element { self.op(OP_FONT_SIZE_PX, 1, float_bits(value)) }
pub fn Element::width_percent(self : Element, value : Float) -> Element { self.op(OP_WIDTH_PERCENT, 1, float_bits(value)) }
pub fn Element::height_percent(self : Element, value : Float) -> Element { self.op(OP_HEIGHT_PERCENT, 1, float_bits(value)) }
pub fn Element::grow(self : Element) -> Element { self.op(OP_FLEX_GROW, 0, 0UL) }
pub fn Element::background(self : Element, rgba : UInt) -> Element { self.op(OP_BACKGROUND_RGBA, 2, rgba.to_uint64()) }
pub fn Element::text_color(self : Element, rgba : UInt) -> Element { self.op(OP_TEXT_RGBA, 2, rgba.to_uint64()) }

pub fn Element::child(self : Element, child : Element) -> Element {
  frame_child(self.frame.handle, self.id, child.id)
  self
}

pub fn Element::on_click(self : Element, handler : () -> Int) -> Element {
  self.frame.handlers.push(handler)
  self.op(OP_ON_CLICK, 3, self.frame.handlers.length().to_uint64())
}
