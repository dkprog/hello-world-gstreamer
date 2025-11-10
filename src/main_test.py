import main
from freezegun import freeze_time
from unittest.mock import patch, MagicMock, ANY
from gi.repository import Gst  # type: ignore


@freeze_time("2026-01-02 13:14:15.123456")
def test_get_gif_file_name():
    filename = main.get_gif_file_name()

    assert filename == "image_2026-01-02T131415.gif"


@patch("main.Gst.Caps.from_string")
@patch("main.Gst.ElementFactory.make")
def test_create_main_src_caps_filter(mock_make, mock_caps):
    capsfilter = MagicMock(name="main_src_capsfilter")
    mock_make.side_effect = lambda name, alias, **__: capsfilter if alias == "main_src_capsfilter" else MagicMock(
        name=alias)
    width, height = main.MAIN_VIDEO_SIZE
    expected_caps = f"video/x-raw, width={width}, height={height}"

    element = main.create_main_src_caps_filter()

    assert element == capsfilter
    mock_caps.assert_called_once_with(expected_caps)
    mock_caps_instance = mock_caps.return_value
    capsfilter.set_property.assert_called_once_with("caps", mock_caps_instance)


@patch("main.Gst.Caps.from_string")
@patch("main.Gst.ElementFactory.make")
def test_create_pip_src_capsfilter(mock_make, mock_caps):
    capsfilter = MagicMock(name="main_src_capsfilter")
    mock_make.side_effect = lambda name, alias, **__: capsfilter if alias == "pip_src_capsfilter" else MagicMock(
        name=alias)
    width, height = main.PIP_VIDEO_SIZE
    expected_caps = f"video/x-raw, width={width}, height={height}"

    element = main.create_pip_src_capsfilter()

    assert element == capsfilter
    mock_caps.assert_called_once_with(expected_caps)
    mock_caps_instance = mock_caps.return_value
    capsfilter.set_property.assert_called_once_with("caps", mock_caps_instance)


@patch("main.Gst.ElementFactory.make")
def test_create_valve(mock_make):
    valve = MagicMock(name="valve")
    mock_make.side_effect = lambda name, alias, **__: valve if alias == "valve" else MagicMock(
        name=alias)

    element = main.create_valve()

    assert element == valve
    valve.set_property.assert_any_call("drop", False)
    valve.set_property.assert_any_call("drop-mode", "transform-to-gap")


@patch("main.Gst.ElementFactory.make")
def test_create_gifenc(mock_make):
    gifenc = MagicMock(name="gifenc")
    mock_make.side_effect = lambda name, alias, **__: gifenc if alias == "gifenc" else MagicMock(
        name=alias)
    fps_n, _ = main.OUTPUT_FPS

    element = main.create_gifenc()

    assert element == gifenc
    gifenc.set_property.assert_any_call("repeat", -1)
    gifenc.set_property.assert_any_call("speed", fps_n)


@patch("main.get_gif_file_name")
@patch("main.Gst.ElementFactory.make")
def test_create_sink(mock_make, mock_gif_file_name):
    sink = MagicMock(name="filesink")
    mock_make.side_effect = lambda name, alias, **__: sink if alias == "sink" else MagicMock(
        name=alias)
    mock_gif_file_name.return_value = "image.gif"

    element = main.create_sink()

    assert element == sink
    sink.set_property.assert_any_call(
        "location", mock_gif_file_name.return_value)


@patch("main.Gst.Caps.from_string")
@patch("main.Gst.ElementFactory.make")
def test_create_elements(mock_make, mock_caps):
    pipeline = MagicMock()
    elements = [
        ("videotestsrc", "main_src"),
        ("capsfilter", "main_src_capsfilter"),
        ("compositor", "compositor"),
        ("v4l2src", "pip_src"),
        ("capsfilter", "pip_src_capsfilter"),
        ("videoconvert", "videoconvert"),
        ("capsfilter", "output_capsfilter"),
        ("tee", "tee"),
        ("queue", "queue_display"),
        ("autovideosink", "sink_display"),
        ("valve", "valve"),
        ("queue", "queue_filesink"),
        ("gifenc", "gifenc"),
        ("filesink", "sink"),
    ]
    mocks = {alias: MagicMock(name=name) for name, alias in elements}
    mock_make.side_effect = lambda name, alias, **__: mocks.get(
        alias, MagicMock(name=alias))

    main.create_elements(pipeline=pipeline)

    for name, alias in elements:
        mock_make.assert_any_call(name, alias)

    for element_mock in mocks.values():
        pipeline.add.assert_any_call(element_mock)


@patch("main.Gst.Caps.from_string")
@patch("main.Gst.ElementFactory.make")
def test_use_queues_with_leaky_downstream(mock_make, mock_caps):
    pipeline = MagicMock()
    elements = [
        ("queue", "queue_display"),
        ("queue", "queue_filesink"),
    ]
    mocks = {alias: MagicMock(name=name) for name, alias in elements}
    mock_make.side_effect = lambda name, alias, **__: mocks.get(
        alias, MagicMock(name=alias))

    main.create_elements(pipeline=pipeline)

    for queue_mock in mocks.values():
        queue_mock.set_property.assert_any_call("leaky", "downstream")


def test_link_elements():
    pipeline = MagicMock()
    elements = [
        ("videotestsrc", "main_src"),
        ("capsfilter", "main_src_capsfilter"),
        ("compositor", "compositor"),
        ("v4l2src", "pip_src"),
        ("capsfilter", "pip_src_capsfilter"),
        ("videoconvert", "videoconvert"),
        ("capsfilter", "output_capsfilter"),
        ("tee", "tee"),
        ("queue", "queue_display"),
        ("autovideosink", "sink_display"),
        ("valve", "valve"),
        ("queue", "queue_filesink"),
        ("gifenc", "gifenc"),
        ("filesink", "sink"),
    ]
    mocks = {alias: MagicMock(name=name) for name, alias in elements}
    pipeline.get_by_name.side_effect = lambda alias, **__: mocks.get(
        alias, MagicMock(name=alias))
    links = [
        # main_src -> compositor
        ("main_src", "main_src_capsfilter"),
        ("main_src_capsfilter", "compositor"),

        # pip_src -> compositor
        ("pip_src", "pip_src_capsfilter"),
        ("pip_src_capsfilter", "compositor"),

        # compositor -> tee
        ("compositor", "videoconvert"),
        ("videoconvert", "output_capsfilter"),
        ("output_capsfilter", "tee"),

        # tee -> sink_display
        ("tee", "queue_display"),
        ("queue_display", "sink_display"),

        # tee -> sink
        ("tee", "valve"),
        ("valve", "queue_filesink"),
        ("queue_filesink", "gifenc"),
        ("gifenc", "sink"),
    ]

    main.link_elements(pipeline=pipeline)

    for src, dst in links:
        mocks[src].link.assert_any_call(mocks[dst])


def test_connect_pip_video_into_compositor():
    pipeline = MagicMock()
    elements = [
        ("compositor", "compositor"),
    ]
    mocks = {alias: MagicMock(name=name) for name, alias in elements}
    pipeline.get_by_name.side_effect = lambda alias, **__: mocks.get(
        alias, MagicMock(name=alias))
    static_pad = MagicMock(name="sink_1")
    mocks["compositor"].get_static_pad.side_effect = lambda name, **__: static_pad if name == "sink_1" else MagicMock(
        name=name)
    xpos, ypos = main.PIP_VIDEO_POSITION

    main.link_elements(pipeline=pipeline)

    static_pad.set_property.assert_any_call("xpos", xpos)
    static_pad.set_property.assert_any_call("ypos", ypos)


@patch("main.link_elements")
@patch("main.create_elements")
@patch("main.Gst.Pipeline.new")
def test_create_pipeline(mock_new_pipeline, mock_create_elements, mock_link_elements):
    pipeline = MagicMock()
    mock_new_pipeline.return_value = pipeline

    result = main.create_pipeline()

    assert result == pipeline
    mock_create_elements.assert_called_once_with(pipeline=pipeline)
    mock_link_elements.assert_called_once_with(pipeline=pipeline)


def test_play_pipeline():
    pipeline = MagicMock()

    main.play_pipeline(pipeline=pipeline)

    pipeline.set_state.assert_called_once_with(Gst.State.PLAYING)


def test_stop_recording():
    pipeline = MagicMock()
    elements = [
        ("valve", "valve"),
        ("queue", "queue_filesink"),
        ("gifenc", "gifenc"),
        ("filesink", "sink"),
    ]
    mocks = {alias: MagicMock(name=name) for name, alias in elements}
    pipeline.get_by_name.side_effect = lambda alias, **__: mocks.get(
        alias, MagicMock(name=alias))

    main.stop_recording(pipeline=pipeline)

    mocks["valve"].set_property.assert_any_call("drop", True)
    mocks["queue_filesink"].set_state.assert_called_once_with(Gst.State.NULL)
    mocks["gifenc"].set_state.assert_called_once_with(Gst.State.NULL)
    mocks["sink"].set_state.assert_called_once_with(Gst.State.NULL)


@patch("main.get_gif_file_name")
def test_resume_recording(mock_gif_file_name):
    mock_gif_file_name.return_value = "image_1.gif"
    pipeline = MagicMock()
    elements = [
        ("valve", "valve"),
        ("queue", "queue_filesink"),
        ("gifenc", "gifenc"),
        ("filesink", "sink"),
    ]
    mocks = {alias: MagicMock(name=name) for name, alias in elements}
    pipeline.get_by_name.side_effect = lambda alias, **__: mocks.get(
        alias, MagicMock(name=alias))

    main.resume_recording(pipeline=pipeline)

    mocks["sink"].set_property.assert_any_call(
        "location", mock_gif_file_name.return_value)
    mocks["queue_filesink"].set_state.assert_called_once_with(
        Gst.State.PLAYING)
    mocks["gifenc"].set_state.assert_called_once_with(Gst.State.PLAYING)
    mocks["sink"].set_state.assert_called_once_with(Gst.State.PLAYING)
    mocks["valve"].set_property.assert_any_call("drop", False)


@patch("main.resume_recording")
@patch("main.stop_recording")
def test_rotate_recording(mock_stop_recording, mock_resume_recording):
    pipeline = MagicMock()

    main.rotate_recording(pipeline=pipeline)

    mock_stop_recording.assert_called_once_with(pipeline=pipeline)
    mock_resume_recording.assert_called_once_with(pipeline=pipeline)


@patch("main.GLib.timeout_add")
def test_configure_timers_calls_timeout_add(mock_timeout_add):
    pipeline = MagicMock()
    duration_ms = main.GIF_DURATION_SECONDS * 1000

    main.configure_timers(pipeline=pipeline)

    mock_timeout_add.assert_called_once_with(duration_ms, ANY)


@patch("main.rotate_recording")
@patch("main.GLib.timeout_add")
def test_on_interval_callback(mock_timeout_add, mock_rotate_recording):
    pipeline = MagicMock()
    captured_callback = None

    def fake_timeout_add(duration, callback):
        nonlocal captured_callback
        captured_callback = callback
        return True
    mock_timeout_add.side_effect = fake_timeout_add
    main.configure_timers(pipeline=pipeline)

    result = captured_callback()

    assert result is True
    mock_rotate_recording.assert_called_once_with(pipeline=pipeline)


@patch("main.Gst.Event.new_eos")
def test_stop_pipeline(mock_new_eos):
    pipeline = MagicMock()
    bus = MagicMock(name="bus")
    eos = MagicMock(name="eos")
    pipeline.get_bus.return_value = bus
    mock_new_eos.return_value = eos

    main.stop_pipeline(pipeline=pipeline)

    pipeline.send_event.assert_called_once_with(eos)
    bus.timed_pop_filtered.assert_called_once_with(
        Gst.CLOCK_TIME_NONE, Gst.MessageType.EOS | Gst.MessageType.ERROR)
    pipeline.set_state.assert_called_once_with(Gst.State.NULL)
