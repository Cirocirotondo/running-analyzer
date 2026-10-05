import pytest

from synthetic import make_video


@pytest.fixture(scope="session")
def phone_video(tmp_path_factory):
    """A slow-motion-like clip: 300 frames, 1.6 s gap after the first, 5 frames dropped after frame 150."""
    return make_video(tmp_path_factory.mktemp("videos") / "phone.mp4")
