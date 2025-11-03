import gi  # type: ignore
import sys
gi.require_version("Gst", "1.0")  # noqa
from gi.repository import Gst, GLib  # type: ignore


def create_elements(pipeline: Gst.Pipeline) -> None:
    src = Gst.ElementFactory.make("videotestsrc", "src")
    pipeline.add(src)

    videoconvert = Gst.ElementFactory.make("videoconvert", "videoconvert")
    pipeline.add(videoconvert)

    sink = Gst.ElementFactory.make("autovideosink", "sink")
    pipeline.add(sink)


def link_elements(pipeline: Gst.Pipeline) -> None:
    src = pipeline.get_by_name("src")
    videoconvert = pipeline.get_by_name("videoconvert")
    sink = pipeline.get_by_name("sink")

    src.link(videoconvert)
    videoconvert.link(sink)


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
    print("Sending EOS...")

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
