"""BlenderFDS, preferences panel"""

from bpy.types import AddonPreferences
from bpy.props import BoolProperty, StringProperty

# Get preference value like this:
# bpy.context.user_preferences.addons["zzz_blenderfds"].preferences.bf_pref_simplify_ui

class BFPreferences(AddonPreferences):
    bl_idname = "zzz_blenderfds"

    bf_pref_simplify_ui = BoolProperty(
            name="Simplify Blender User Interface (Blender restart needed)",
            description="Simplify Blender User Interface (Blender restart needed)",
            default=True,
            )

    bf_pref_use_custom_snippet_path = BoolProperty(
            name="Use Custom Snippets Path",
            description="Use Custom Snippets Path",
            default=False,
            )

    bf_pref_custom_snippet_path = StringProperty(
            name="Custom Snippets Path",
            description="Custom Snippets Path",
            subtype="DIR_PATH",
            maxlen=1024,
            )

    def draw(self, context):
        layout = self.layout
        # UI
        row = layout.split(.3)
        row.operator("wm.bf_load_blenderfds_settings", icon='LOAD_FACTORY')
        layout.prop(self, "bf_pref_simplify_ui")
        layout.prop(context.user_preferences.filepaths, "use_load_ui", text="Reset User Interface on File Load")
        # Paths
        row = layout.row()
        col_export, col = row.column(), row.column()
        col_export.prop(self, "bf_pref_use_custom_snippet_path", text="")
        col.prop(self, "bf_pref_custom_snippet_path")
        col.active = bool(self.bf_pref_use_custom_snippet_path) # if not used, layout is inactive
        # Mouse button selection
        row = layout.row()
        row.label("Mouse Select With Button:")
        row.prop(context.user_preferences.inputs, "select_mouse", expand=True)
        return layout
