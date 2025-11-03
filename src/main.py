import gi  # type: ignore
import sys
gi.require_version("Gst", "1.0")  # noqa
from gi.repository import Gst, GLib  # type: ignore

MAIN_VIDEO_SIZE = (640, 480)
PIP_VIDEO_SIZE = (320, 240)
PIP_VIDEO_DEVICE = "/dev/video0"
PIP_VIDEO_POSITION = (0, MAIN_VIDEO_SIZE[1]-PIP_VIDEO_SIZE[1])


def create_elements(pipeline: Gst.Pipeline) -> None:
    main_src = Gst.ElementFactory.make("videotestsrc", "main_src")
    pipeline.add(main_src)

    main_src_capsfilter = Gst.ElementFactory.make(
        "capsfilter", "main_src_capsfilter")
    width, height = MAIN_VIDEO_SIZE
    caps = Gst.Caps.from_string(f"video/x-raw, width={width}, height={height}")
    main_src_capsfilter.set_property("caps", caps)
    pipeline.add(main_src_capsfilter)

    compositor = Gst.ElementFactory.make("compositor", "compositor")
    pipeline.add(compositor)

    pip_src = Gst.ElementFactory.make("v4l2src", "pip_src")
    pip_src.set_property("device", PIP_VIDEO_DEVICE)
    pipeline.add(pip_src)

    pip_src_capsfilter = Gst.ElementFactory.make(
        "capsfilter", "pip_src_capsfilter")
    width, height = PIP_VIDEO_SIZE
    caps = Gst.Caps.from_string(f"video/x-raw, width={width}, height={height}")
    pip_src_capsfilter.set_property("caps", caps)
    pipeline.add(pip_src_capsfilter)

    videoconvert = Gst.ElementFactory.make("videoconvert", "videoconvert")
    pipeline.add(videoconvert)

    sink = Gst.ElementFactory.make("autovideosink", "sink")
    pipeline.add(sink)


def link_elements(pipeline: Gst.Pipeline) -> None:
    main_src = pipeline.get_by_name("main_src")
    main_src_capsfilter = pipeline.get_by_name("main_src_capsfilter")
    compositor = pipeline.get_by_name("compositor")
    videoconvert = pipeline.get_by_name("videoconvert")
    sink = pipeline.get_by_name("sink")
    pip_src = pipeline.get_by_name("pip_src")
    pip_src_capsfilter = pipeline.get_by_name("pip_src_capsfilter")

    main_src.link(main_src_capsfilter)
    main_src_capsfilter.link(compositor)
    compositor.link(videoconvert)
    videoconvert.link(sink)
    pip_src.link(pip_src_capsfilter)
    pip_src_capsfilter.link(compositor)

    compositor_sink_1 = compositor.get_static_pad("sink_1")
    xpos, ypos = PIP_VIDEO_POSITION
    compositor_sink_1.set_property("xpos", xpos)
    compositor_sink_1.set_property("ypos", ypos)


def create_pipeline() -> Gst.Pipeline:
    pipeline = Gst.Pipeline.new("hello-world-pipeline")
    create_elements(pipeline=pipeline)
    link_elements(pipeline=pipeline)
    return pipeline


def play_pipeline(pipeline: Gst.Pipeline) -> None:
    pipeline.set_state(Gst.State.PLAYING)
    print("Pipeline is now playing...")


def observe_events(pipeline: Gst.Pipeline, loop: GLib.MainLoop) -> None:
    bus = pipeline.get_bus()
    bus.add_signal_watch()

    def on_message(bus: Gst.Bus, message: Gst.Message, pipeline: Gst.Pipeline) -> None:
        if message.type == Gst.MessageType.STATE_CHANGED:
            if message.src == pipeline:
                old, new, pending = message.parse_state_changed()
                print(
                    f"Pipeline state {old.value_nick.upper()} => {new.value_nick.upper()}")
                if new == Gst.State.PLAYING:
                    # when GST_DEBUG_DUMP_DOT_DIR is set, create pipeline.dot
                    Gst.debug_bin_to_dot_file(
                        pipeline, Gst.DebugGraphDetails.ALL, "pipeline")
        elif message.type == Gst.MessageType.ERROR:
            err, dbg = message.parse_error()
            print("Error:", err, dbg)
            sys.exit(1)
        elif message.type == Gst.MessageType.EOS:
            print("Got EOS.")
            loop.quit()


def stop_pipeline(pipeline: Gst.Pipeline):
    print("Sending EOS event...")

    bus = pipeline.get_bus()
    eos = Gst.Event.new_eos()
    pipeline.send_event(eos)

    msg = bus.timed_pop_filtered(
        Gst.CLOCK_TIME_NONE, Gst.MessageType.EOS | Gst.MessageType.ERROR)
    if msg.type == Gst.MessageType.EOS:
        print("EOS received, leaving gracefully")
    elif msg.type == Gst.MessageType.ERROR:
        err, dbg = msg.parse_error()
        print("ERROR on shutdown:", err, dbg)

    print("Stopping the pipeline...")
    pipeline.set_state(Gst.State.NULL)


if __name__ == '__main__':
    # Initialize GStreamer
    Gst.init(None)

    # Create a GStreamer pipeline
    loop = GLib.MainLoop()
    pipeline = create_pipeline()
    observe_events(pipeline=pipeline, loop=loop)
    play_pipeline(pipeline=pipeline)

    try:
        loop.run()
    except KeyboardInterrupt:
        stop_pipeline(pipeline=pipeline)
        loop.quit()
    print("Goodbye.")
