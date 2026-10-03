#external
type FrameHandle

extern "C" fn host_start(
  render : FuncRef[(FrameHandle) -> Int],
  click : FuncRef[(Int) -> Int],
  started : FuncRef[() -> Int],
) -> Int = "gpui_moon_host_start"

#borrow(title)
extern "C" fn host_open(title : Bytes, length : Int) -> Int = "gpui_moon_host_open"

extern "C" fn host_invalidate() -> Int = "gpui_moon_host_invalidate"

#borrow(text)
extern "C" fn frame_node(frame : FrameHandle, kind : Int, text : Bytes, length : Int) -> Int = "gpui_moon_frame_node"

extern "C" fn frame_op(frame : FrameHandle, node : Int, code : Int, kind : Int, value : UInt64) -> Unit = "gpui_moon_frame_op"

extern "C" fn frame_child(frame : FrameHandle, parent : Int, child : Int) -> Unit = "gpui_moon_frame_child"

extern "C" fn frame_finish(frame : FrameHandle, root : Int) -> Int = "gpui_moon_frame_finish"

extern "C" fn float_bits(value : Float) -> UInt64 = "gpui_moon_float_bits"
