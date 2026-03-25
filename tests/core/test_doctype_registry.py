"""
SPEC-002 / STORY-004: Doctype Registry & Catalog
"""

from team_mind_mcp.server import (
    DoctypeSpec,
    ToolProvider,
    IngestProcessor,
    PluginRegistry,
)


class _PluginA(ToolProvider):
    @property
    def name(self) -> str:
        return "plugin_a"

    @property
    def doctypes(self) -> list[DoctypeSpec]:
        return [
            DoctypeSpec(name="type_x", description="Type X from A"),
            DoctypeSpec(name="type_y", description="Type Y from A"),
        ]


class _PluginB(IngestProcessor):
    @property
    def name(self) -> str:
        return "plugin_b"

    @property
    def doctypes(self) -> list[DoctypeSpec]:
        return [
            DoctypeSpec(name="type_z", description="Type Z from B"),
        ]


class _PluginC(ToolProvider):
    """Plugin that also declares type_x (same doctype name as PluginA)."""

    @property
    def name(self) -> str:
        return "plugin_c"

    @property
    def doctypes(self) -> list[DoctypeSpec]:
        return [
            DoctypeSpec(name="type_x", description="Type X from C"),
            DoctypeSpec(name="type_w", description="Type W from C"),
        ]


class _BarePlugin(ToolProvider):
    @property
    def name(self) -> str:
        return "bare_plugin"


def test_catalog_collects_on_registration():
    """
    AC-001: Catalog Collects Doctypes on Registration
    """
    registry = PluginRegistry()

    # Given a plugin that declares two doctypes
    plugin = _PluginA()

    # When the plugin is registered with the PluginRegistry
    registry.register(plugin)

    # Then both doctypes appear in the registry's internal catalog
    catalog = registry.get_doctype_catalog()
    assert len(catalog) == 2

    # And each doctype's plugin field is set to the registering plugin's name
    assert all(dt.plugin == "plugin_a" for dt in catalog)


def test_get_all_doctypes():
    """
    AC-002: Get All Doctypes
    """
    registry = PluginRegistry()

    # Given three plugins are registered, declaring a total of five doctypes
    registry.register(_PluginA())  # 2 doctypes
    registry.register(_PluginB())  # 1 doctype
    registry.register(_PluginC())  # 2 doctypes

    # When get_doctype_catalog() is called
    catalog = registry.get_doctype_catalog()

    # Then all five DoctypeSpec instances are returned
    assert len(catalog) == 5


def test_get_doctypes_for_plugin():
    """
    AC-003: Get Doctypes for Plugin
    """
    registry = PluginRegistry()

    # Given "plugin_a" declares ["type_x", "type_y"] and "plugin_b" declares ["type_z"]
    registry.register(_PluginA())
    registry.register(_PluginB())

    # When get_doctypes_for_plugin("plugin_a") is called
    result = registry.get_doctypes_for_plugin("plugin_a")

    # Then exactly ["type_x", "type_y"] are returned
    names = [dt.name for dt in result]
    assert sorted(names) == ["type_x", "type_y"]


def test_get_plugins_for_doctype():
    """
    AC-004: Get Plugins for Doctype
    """
    registry = PluginRegistry()

    # Given "plugin_a" and "plugin_c" both declare a doctype named "type_x"
    registry.register(_PluginA())
    registry.register(_PluginC())

    # When get_plugins_for_doctype("type_x") is called
    result = registry.get_plugins_for_doctype("type_x")

    # Then both "plugin_a" and "plugin_c" are returned
    assert sorted(result) == ["plugin_a", "plugin_c"]


def test_plugin_with_no_doctypes():
    """
    AC-005: Plugin with No Doctypes
    """
    registry = PluginRegistry()
    registry.register(_PluginA())  # 2 doctypes

    # Given a plugin that does not override the doctypes property
    # When it is registered with the PluginRegistry
    registry.register(_BarePlugin())

    # Then the catalog is not modified (still 2)
    assert len(registry.get_doctype_catalog()) == 2
    # And no error is raised (implicit)


def test_doctype_specs_include_plugin_name():
    """
    AC-006: Doctype Specs Include Plugin Name
    """
    registry = PluginRegistry()

    # Given a plugin named "plugin_b" declares a doctype "type_z"
    registry.register(_PluginB())

    # When the doctype is retrieved from the catalog
    catalog = registry.get_doctype_catalog()
    dt = catalog[0]

    # Then the DoctypeSpec.plugin field equals "plugin_b"
    assert dt.plugin == "plugin_b"
    assert dt.name == "type_z"
