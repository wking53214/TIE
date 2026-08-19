from tie import create_source, segment_source, build_package


def test_package_serializes_to_json():
    source = create_source("s", "text")
    package = build_package(package_id="p", source=source, coverage=segment_source(source))
    text = package.to_json()
    assert '"package_id": "p"' in text
    assert '"source_id": "s"' in text
