import importlib
import json
import logging
from mcp.types import Tool, TextContent
from team_mind_mcp.server import (
    ToolProvider,
    IngestProcessor,
    IngestObserver,
    PluginRegistry,
    EventFilter,
)
from team_mind_mcp.storage import StorageAdapter

logger = logging.getLogger(__name__)


class PluginLoader:
    """Imports and instantiates plugins from module paths."""

    @staticmethod
    def load(
        module_path: str,
        storage: StorageAdapter | None = None,
        config: dict | None = None,
    ):
        """Load a plugin class from a dotted module path.

        module_path format: "package.module.ClassName"
        """
        parts = module_path.rsplit(".", 1)
        if len(parts) != 2:
            raise ValueError(
                f"Invalid module_path: {module_path}. Expected 'module.ClassName'."
            )

        module_name, class_name = parts
        try:
            module = importlib.import_module(module_name)
        except ImportError as e:
            raise ValueError(f"Could not import module '{module_name}': {e}")

        cls = getattr(module, class_name, None)
        if cls is None:
            raise ValueError(
                f"Class '{class_name}' not found in module '{module_name}'."
            )

        # Try to instantiate with storage, then config, then no args
        try:
            if storage is not None and config is not None:
                return cls(storage=storage, **config)
            elif storage is not None:
                return cls(storage)
            elif config is not None:
                return cls(**config)
            else:
                return cls()
        except TypeError:
            # Fallback: try with no args
            return cls()

    @staticmethod
    def apply_event_filter(plugin, event_filter_json: dict | None) -> None:
        """Apply a serialized EventFilter to an observer plugin."""
        if event_filter_json is None or not isinstance(plugin, IngestObserver):
            return
        ef = EventFilter(
            plugins=event_filter_json.get("plugins"),
            doctypes=event_filter_json.get("doctypes"),
        )
        # Store the filter on the instance for observers that use default property
        plugin._event_filter_override = ef

    @staticmethod
    def get_plugin_type(plugin) -> str:
        """Determine the plugin type string from its interfaces."""
        types = []
        if isinstance(plugin, ToolProvider):
            types.append("tool_provider")
        if isinstance(plugin, IngestProcessor):
            types.append("ingest_processor")
        if isinstance(plugin, IngestObserver):
            types.append("ingest_observer")
        return ",".join(types) if types else "unknown"


class LifecyclePlugin(ToolProvider):
    """MCP tools for dynamic plugin registration and management."""

    def __init__(self, registry: PluginRegistry, storage: StorageAdapter):
        self.registry = registry
        self.storage = storage

    @property
    def name(self) -> str:
        return "lifecycle_plugin"

    def get_tools(self) -> list[Tool]:
        return [
            Tool(
                name="register_plugin",
                description="Dynamically register a new plugin from a Python module path.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "module_path": {
                            "type": "string",
                            "description": "Dotted Python path to the plugin class (e.g., 'my_plugins.travel.TravelPlugin').",
                        },
                        "config": {
                            "type": "object",
                            "description": "Optional plugin-specific configuration.",
                        },
                        "event_filter": {
                            "type": "object",
                            "description": "Optional event subscription filter with 'plugins' and/or 'doctypes' lists.",
                        },
                    },
                    "required": ["module_path"],
                },
            ),
            Tool(
                name="unregister_plugin",
                description="Unregister a dynamically loaded plugin by name.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "plugin_name": {
                            "type": "string",
                            "description": "Name of the plugin to unregister.",
                        }
                    },
                    "required": ["plugin_name"],
                },
            ),
            Tool(
                name="list_plugins",
                description="List all registered plugins and their status.",
                inputSchema={"type": "object", "properties": {}},
            ),
        ]

    async def call_tool(self, name: str, arguments: dict) -> list[TextContent]:
        if name == "register_plugin":
            return await self._register(arguments)
        elif name == "unregister_plugin":
            return await self._unregister(arguments)
        elif name == "list_plugins":
            return await self._list()
        raise ValueError(f"Unsupported tool: {name}")

    async def _register(self, arguments: dict) -> list[TextContent]:
        module_path = arguments.get("module_path")
        config = arguments.get("config")
        event_filter = arguments.get("event_filter")

        if not module_path:
            raise ValueError("module_path is required")

        # Load and instantiate
        plugin = PluginLoader.load(module_path, storage=self.storage, config=config)

        # Check for duplicate
        if (
            plugin.name in self.registry._tool_providers
            or any(p.name == plugin.name for p in self.registry._ingest_processors)
            or any(o.name == plugin.name for o in self.registry._ingest_observers)
        ):
            raise ValueError(f"Plugin '{plugin.name}' is already registered.")

        # Apply event filter if observer
        PluginLoader.apply_event_filter(plugin, event_filter)

        # Register
        self.registry.register(plugin)

        # Persist
        plugin_type = PluginLoader.get_plugin_type(plugin)
        self.storage.save_plugin_record(
            plugin_name=plugin.name,
            plugin_type=plugin_type,
            module_path=module_path,
            config=config,
            event_filter_json=event_filter,
        )

        tools_registered = []
        if isinstance(plugin, ToolProvider):
            tools_registered = [t.name for t in plugin.get_tools()]

        result = {
            "status": "registered",
            "plugin_name": plugin.name,
            "plugin_type": plugin_type,
            "tools_registered": tools_registered,
        }
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    async def _unregister(self, arguments: dict) -> list[TextContent]:
        plugin_name = arguments.get("plugin_name")
        if not plugin_name:
            raise ValueError("plugin_name is required")

        removed_tools = self.registry.unregister(plugin_name)
        self.storage.disable_plugin_record(plugin_name)

        result = {
            "status": "unregistered",
            "plugin_name": plugin_name,
            "tools_removed": removed_tools,
        }
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    async def _list(self) -> list[TextContent]:
        plugins = []

        # Core plugins (from registry)
        seen = set()
        for pname, provider in self.registry._tool_providers.items():
            tools = [t.name for t in provider.get_tools()]
            plugins.append(
                {
                    "name": pname,
                    "plugin_type": PluginLoader.get_plugin_type(provider),
                    "tools": tools,
                    "source": "runtime",
                }
            )
            seen.add(pname)

        for proc in self.registry._ingest_processors:
            if proc.name not in seen:
                plugins.append(
                    {
                        "name": proc.name,
                        "plugin_type": PluginLoader.get_plugin_type(proc),
                        "tools": [],
                        "source": "runtime",
                    }
                )
                seen.add(proc.name)

        for obs in self.registry._ingest_observers:
            if obs.name not in seen:
                ef = obs.event_filter
                plugins.append(
                    {
                        "name": obs.name,
                        "plugin_type": PluginLoader.get_plugin_type(obs),
                        "tools": [],
                        "event_filter": {
                            "plugins": ef.plugins,
                            "doctypes": ef.doctypes,
                        }
                        if ef
                        else None,
                        "source": "runtime",
                    }
                )
                seen.add(obs.name)

        return [TextContent(type="text", text=json.dumps(plugins, indent=2))]


def load_persisted_plugins(
    storage: StorageAdapter,
    registry: PluginRegistry,
) -> int:
    """Load enabled plugins from the persistence table on startup.

    Returns the number of plugins successfully loaded.
    Failed loads are logged as warnings but don't block startup.
    """
    records = storage.get_enabled_plugin_records()
    loaded = 0

    for record in records:
        try:
            plugin = PluginLoader.load(
                record["module_path"],
                storage=storage,
                config=record.get("config"),
            )
            PluginLoader.apply_event_filter(plugin, record.get("event_filter"))
            registry.register(plugin)
            loaded += 1
            logger.info(f"Loaded persisted plugin: {record['plugin_name']}")
        except Exception as e:
            logger.warning(
                f"Failed to load plugin '{record['plugin_name']}' "
                f"from '{record['module_path']}': {e}"
            )

    return loaded
