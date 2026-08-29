"""The parts of the usage engine that work on files alone."""

from __future__ import annotations

import json

from custom_components.integrationguard.usage import files, orphans, plugins, themes


def bundle(tmp_path, repo: str, name: str, content: str):
    """Write a fake plugin bundle the way HACS would install it."""
    directory = tmp_path / "www" / "community" / repo
    directory.mkdir(parents=True, exist_ok=True)
    (directory / name).write_text(content, encoding="utf-8")
    return tmp_path / "www" / "community"


def test_plain_card_is_found_forwards(tmp_path):
    community = bundle(
        tmp_path,
        "demo-card",
        "demo-card.js",
        'customElements.define("demo-card",D);'
        "window.customCards=window.customCards||[],"
        'window.customCards.push({type:"demo-card",name:"Demo"})',
    )
    found = plugins.read_plugin_files(community, "someone/demo-card", set())
    assert found.defined == {"demo-card"}
    assert found.registered == {"demo-card"}


def test_card_registered_through_a_helper_is_found_backwards(tmp_path):
    """Mushroom builds its card list from variables, so only this half works."""
    community = bundle(
        tmp_path,
        "lovelace-mushroom",
        "mushroom.js",
        "o.customCards=o.customCards||[];o.customCards.push(ee({},t));"
        'const CARDS=["mushroom-template-card","mushroom-light-card"];',
    )
    found = plugins.read_plugin_files(
        community, "piitaya/lovelace-mushroom", {"mushroom-template-card"}
    )
    assert found.registered == set()
    assert found.matched == {"mushroom-template-card"}


def test_a_type_nobody_uses_is_not_matched(tmp_path):
    community = bundle(tmp_path, "demo-card", "demo.js", 'define("demo-card")')
    found = plugins.read_plugin_files(community, "someone/demo-card", {"other-card"})
    assert found.matched == set()


def test_a_library_yields_no_types(tmp_path):
    """card-mod and friends must end up undetermined, never unused."""
    community = bundle(
        tmp_path, "lovelace-card-mod", "card-mod.js", "const applyStyles=()=>{};"
    )
    found = plugins.read_plugin_files(community, "thomasloven/lovelace-card-mod", set())
    assert found.types == set()


def test_a_missing_directory_is_no_error(tmp_path):
    found = plugins.read_plugin_files(tmp_path, "someone/never-installed", set())
    assert found.directory is None
    assert found.files == []


def test_directory_is_matched_regardless_of_case(tmp_path):
    community = bundle(tmp_path, "Bubble-Card", "bubble.js", 'define("bubble-card")')
    found = plugins.read_plugin_files(community, "clooos/bubble-card", set())
    assert found.directory is not None


def test_registration_is_read_from_the_resources(tmp_path):
    community = bundle(tmp_path, "demo-card", "demo.js", "")
    directory = community / "demo-card"
    assert plugins.is_registered(["/hacsfiles/demo-card/demo.js?v=1"], directory)
    assert plugins.is_registered(["/local/community/demo-card/demo.js"], directory)
    assert not plugins.is_registered(["/hacsfiles/other/other.js"], directory)
    assert not plugins.is_registered([], None)


def test_dead_resources_are_found(tmp_path):
    (tmp_path / "www" / "community" / "alive").mkdir(parents=True)
    (tmp_path / "www" / "community" / "alive" / "alive.js").write_text("")
    result = orphans.find(
        tmp_path,
        ["/hacsfiles/alive/alive.js?v=1", "/hacsfiles/ghost/ghost.js"],
        {"alive"},
        set(),
    )
    kinds = {(item["kind"], item.get("url") or item.get("name")) for item in result}
    assert ("dead_resource", "/hacsfiles/ghost/ghost.js") in kinds
    assert not any(
        item["kind"] == "dead_resource" and "alive" in item["url"] for item in result
    )


def test_unknown_directories_are_reported(tmp_path):
    (tmp_path / "www" / "community" / "known").mkdir(parents=True)
    (tmp_path / "www" / "community" / "leftover").mkdir(parents=True)
    (tmp_path / "custom_components" / "known_domain").mkdir(parents=True)
    (tmp_path / "custom_components" / "hand_installed").mkdir(parents=True)
    result = orphans.find(tmp_path, [], {"known"}, {"known_domain"})
    names = {item.get("name") for item in result}
    assert names == {"leftover", "hand_installed"}


def test_theme_names_come_from_the_file_contents(tmp_path):
    directory = tmp_path / "themes"
    directory.mkdir()
    (directory / "my-theme.yaml").write_text(
        "my_dark:\n  primary-color: '#000'\nmy_light:\n  primary-color: '#fff'\n"
    )
    names = themes.theme_names(directory, "someone/my-theme")
    assert {"my_dark", "my_light", "my-theme"} <= names


def test_selected_themes_are_read_per_user(tmp_path):
    storage = tmp_path / ".storage"
    storage.mkdir()
    (storage / "frontend.user_data_abc").write_text(
        json.dumps({"data": {"themes": {"theme": "my_dark", "dark_theme": "my_light"}}})
    )
    chosen, readable = themes.selected_themes(storage)
    assert chosen == {"my_dark", "my_light"}
    assert readable is True


def test_no_user_files_means_no_answer(tmp_path):
    chosen, readable = themes.selected_themes(tmp_path)
    assert chosen == set()
    assert readable is False


def test_the_corpus_covers_configuration_and_storage(tmp_path):
    (tmp_path / "automations.yaml").write_text("- action: python_script.tidy_up\n")
    storage = tmp_path / ".storage"
    storage.mkdir()
    (storage / "lovelace.dash").write_text('{"config": {"template": "greeting.jinja"}}')
    (tmp_path / "custom_components").mkdir()
    (tmp_path / "custom_components" / "noise.yaml").write_text(
        "python_script.ignore_me"
    )
    corpus = files.read_corpus(tmp_path)
    assert "python_script.tidy_up" in corpus
    assert "greeting.jinja" in corpus
    assert "ignore_me" not in corpus
