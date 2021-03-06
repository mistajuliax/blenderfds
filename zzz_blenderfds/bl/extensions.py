"""BlenderFDS, extended Blender types."""

import bpy, time, sys
from bpy.types import Object, Material, Scene

from ..types import BFNamelist
from ..exceptions import BFException
from .. import geometry
from .. import fds

DEBUG = False


# Extend bpy.type.Object

class BFObject():
    """Extend Blender Object bpy.type."""

    def __str__(self):
        return "Object {}".format(self.name)

    @property
    def bf_namelist(self) -> "BFNamelist instance or None":
        """Return an instance of the linked Object namelist class."""
        if self.type != "MESH" or self.bf_is_tmp:
            return None
        # get class from name
        ON_cls = BFNamelist.all.get(self.bf_namelist_cls)
        if ON_cls:
            return ON_cls(element=self)  # create instance from class

    def set_default_appearance(self, context):
        """Set default object appearance."""
        # Get bf_namelist
        bf_namelist = self.bf_namelist
        if not bf_namelist:
            return
        # Set draw_type
        draw_type = bf_namelist.bf_other.get("draw_type")
        if draw_type:
            self.draw_type = draw_type
        # Set show_transparent
        self.show_transparent = True

    # Export to FDS

    def _myself_to_fds(self, context) -> "list":
        """Export myself in FDS notation."""
        bodies = list()
        if self.bf_export:
            if self.type == "MESH":
                bf_namelist = self.bf_namelist
                if bf_namelist:
                    body = bf_namelist.to_fds(context)
                    if body:
                        bodies.append(body)  # could be None
            elif self.type == "EMPTY":
                bodies.append("! -- {}: {}\n".format(self.name, self.bf_fyi))
        return bodies

    def _children_to_fds(self, context) -> "list":
        """Export children in FDS notation."""
        # Init
        children_obs = [ob for ob in context.scene.objects if ob.parent == self]
        children_obs.sort(key=lambda k: k.name)  # Order by element name
        children_obs.sort(key=lambda k: k.bf_namelist_cls != ("ON_MESH"))
        # Children to_fds
        bodies = list()
        for ob in children_obs:
            body = ob.to_fds(context, with_children=True)
            if body:
                bodies.append(body)  # could be None
        if bodies:
            bodies.append("\n")
        # Return
        return bodies

    def to_fds(self, context, with_children=False) -> "str or None":
        """Export myself and children in FDS notation."""
        bodies = list()
        bodies.extend(self._myself_to_fds(context))
        if with_children:
            bodies.extend(self._children_to_fds(context))
        return "".join(bodies)

    # Manage tmp objects

    def set_tmp(self, context, ob):
        """Set self as temporary object of ob."""
        # Link object to context scene
        # context.scene.objects.link(self) # TODO Is it always already linked?
        # Set temporary object
        self.bf_is_tmp = True
        self.active_material = ob.active_material
        self.layers = ob.layers
        # self.groups = ob.groups TODO does not work but would be useful!
        self.show_wire = True
        # Set parenting and keep position
        self.parent = ob
        self.matrix_parent_inverse = ob.matrix_world.inverted()
        # Set parent object
        ob.bf_has_tmp = True

    def show_tmp_obs(self, context):
        """Show my temporary objects."""
        # Show my tmp obs
        for child in self.children:
            if child.bf_is_tmp:
                child.hide = False
        # Set myself hidden but active
        self.select = True
        context.scene.objects.active = self
        self.hide = True

    def remove_tmp_obs(self, context):
        """Remove my temporary objects."""
        # Remove my tmp obs
        for child in self.children:
            if child.bf_is_tmp:
                bpy.data.objects.remove(child, do_unlink=True)
        self.bf_has_tmp = False
        # Set myself visible
        self.hide = False


# Add methods to original Blender type

Object.__str__ = BFObject.__str__
Object.bf_namelist = BFObject.bf_namelist
Object.set_default_appearance = BFObject.set_default_appearance
Object._myself_to_fds = BFObject._myself_to_fds
Object._children_to_fds = BFObject._children_to_fds
Object.to_fds = BFObject.to_fds
Object.set_tmp = BFObject.set_tmp
Object.show_tmp_obs = BFObject.show_tmp_obs
Object.remove_tmp_obs = BFObject.remove_tmp_obs


# Extend bpy.type.Material

class BFMaterial():
    """Extend Blender Material."""

    def __str__(self):
        return "Material {}".format(self.name)

    @property
    def bf_namelist(self) -> "BFNamelist instance or None":
        """Return an instance of the linked Material namelist class."""
        MN_cls = BFNamelist.all.get(self.bf_namelist_cls)
        if MN_cls:
            return MN_cls(element=self)  # create instance from class

    def set_default_appearance(self, context):
        """Set default material appearance."""
        self.use_fake_user = True

    def to_fds(self, context) -> "str or None":
        """Export myself in FDS notation."""
        if self.name not in fds.surf.predefined:
            bf_namelist = self.bf_namelist
            if bf_namelist:
                return bf_namelist.to_fds(context)


# Add methods to original Blender type

Material.__str__ = BFMaterial.__str__
Material.bf_namelist = BFMaterial.bf_namelist
Material.set_default_appearance = BFMaterial.set_default_appearance
Material.to_fds = BFMaterial.to_fds


# Extend bpy.type.Scene

class BFScene():
    """Extend Blender Scene."""

    def __str__(self):
        return "Scene {}".format(self.name)

    @property
    def bf_namelists(self) -> "List of BFNamelist instances":
        """Return a list of instances of the linked Scene namelist classes."""
        bf_namelists = [
            bf_namelist(element=self)
            for bf_namelist in BFNamelist.all if bf_namelist.bpy_type == Scene
        ]
        bf_namelists.sort(key=lambda k: k.enum_id)
        return bf_namelists

    def set_default_appearance(self, context):
        self.unit_settings.system = 'METRIC'
        self.render.engine = 'CYCLES'  # for transparency visualisation

    # Export

    def _myself_to_fds(self, context) -> "list":
        """Export myself in FDS notation."""
        bodies = list()
        for bf_namelist in self.bf_namelists:
            body = bf_namelist.to_fds(context)
            if body:
                bodies.append(body)  # Could be None
        if bodies:
            bodies.append("\n")
        return bodies

    def _children_to_fds(self, context) -> "list":
        """Export children in FDS notation."""
        # Init
        bodies = list()
        # Materials
        bodies.append("\n! --- Boundary conditions (from Blender Materials)\n")
        mas = [ma for ma in bpy.data.materials]
        mas.sort(key=lambda k: k.name)  # Alphabetic order by element name
        for ma in mas:
            body = ma.to_fds(context)
            if body:
                bodies.append(body)
        # Objects
        bodies.append("\n! --- Geometric entities (from Blender Objects)\n")
        bodies.extend(Object._children_to_fds(self=None, context=context))
        # Return
        return bodies

    def _header_to_fds(self, context) -> "tuple":
        """Export header in FDS notation."""
        return (
            "! Generated by BlenderFDS {} on Blender {}\n".format(
                "{0[0]}.{0[1]}.{0[2]}".format(
                    sys.modules['zzz_blenderfds'].bl_info["version"]
                ),
                bpy.app.version_string,
            ),
            "! Case: {} (from Blender Scene)\n".format(self.name),
            "! Description: {}\n".format(self.bf_head_title),
            "! Date: {}\n".format(
                time.strftime("%a, %d %b %Y, %H:%M:%S", time.localtime())
            ),
            "! File: {}\n\n".format(bpy.data.filepath),
        )

    def _free_text_to_fds(self, context) -> "list":
        """Export HEAD free text in FDS notation."""
        bodies = list()
        # HEAD BFNnamelist traps my errors
        if self.bf_head_free_text:
            free_text = bpy.data.texts[self.bf_head_free_text].as_string()
            if not free_text:
                return bodies
            bodies.append("! --- Free text: '{}'\n".format(self.bf_head_free_text))
            bodies.append(bpy.data.texts[self.bf_head_free_text].as_string())
            if bodies[-1][-1:] != "\n":
                bodies.append("\n")
        return bodies

    def to_fds(self, context, with_children=False) -> "str or None":
        """Export myself and children (full FDS case) in FDS notation."""
        # Init
        t0 = time.time()
        bodies = list()
        # Header, Scene, free_text
        if with_children:
            bodies.extend(self._header_to_fds(context))
        bodies.extend(self._myself_to_fds(context))
        bodies.extend(self._free_text_to_fds(context))
        # Materials, objects, TAIL
        if with_children:
            bodies.extend(self._children_to_fds(context))
            bodies.append("&TAIL /\n! Generated in {0:.0f} s.".format(
                (time.time()-t0))
            )
        # Return
        return "".join(bodies)

    def to_ge1(self, context) -> "str or None":
        """Export my geometry in FDS GE1 notation."""
        return geometry.to_ge1.scene_to_ge1(context, self)

    # Import

    def _get_imported_bf_namelist_cls(
        self, context, fds_label, fds_params
    ) -> "BFNamelist or None":
        """Try to get managed BFNamelist from fds_label."""
        bf_namelist_cls = BFNamelist.all.get_by_fds_label(fds_label)
        if not bf_namelist_cls:
            if any(
                (label in fds_params
                    for label in ('XB', 'XYZ', 'PBX', 'PBY', 'PBZ'))
            ):
                # An unmanaged geometric namelist
                bf_namelist_cls = BFNamelist.all["ON_free"]
        return bf_namelist_cls

    def _get_imported_element(
        self, context, bf_namelist_cls, fds_label
    ) -> "Element":
        """Get element."""
        bpy_type = bf_namelist_cls.bpy_type
        if bpy_type == bpy.types.Scene:
            element = self  # Import into self
        elif bpy_type == bpy.types.Object:
            element = geometry.geom_utils.get_new_object(
                context, self, name="New {}".format(fds_label)
            )  # New Object
            # Set link to namelist
            element.bf_namelist_cls = bf_namelist_cls.__name__
        elif bpy_type == bpy.types.Material:
            element = geometry.geom_utils.get_new_material(
                context, name="New {}".format(fds_label)
            )  # New Material
            element.bf_namelist_cls = "MN_SURF"  # Set link to default namelist
        else:
            raise ValueError(
                "BFDS: BFScene.from_fds: Unrecognized namelist type!"
            )
        element.set_default_appearance(context)
        return element

    def _save_imported_unmanaged_tokens(self, context, free_texts) -> "None":
        """Save unmanaged tokens to free text."""
        # Get or create free text file, then show
        bf_head_free_text = fds.head.set_free_text_file(context, self)
        # Get existing contents
        old_free_texts = bpy.data.texts[bf_head_free_text].as_string()
        if old_free_texts:
            free_texts.append(old_free_texts)
        # Write merged contents
        bpy.data.texts[bf_head_free_text].from_string("\n".join(free_texts))

    def from_fds(self, context, value):
        """Import a text in FDS notation into self."""
        tokens = None
        errors = False
        free_texts = list()
        # Tokenize value and manage exception
        try:
            tokens = fds.to_py.tokenize(value)
        except BFException as err:
            errors = True
            free_texts.extend(err.free_texts)  # Record in free_texts
        # Treat tokens, first SURFs
        if tokens:
            for token in sorted(tokens, key=lambda k: k[0] != ("SURF_ID")):
                # Init
                fds_label, fds_params, fds_original = token
                # Search managed FDS namelist, and import token
                bf_namelist_cls = self._get_imported_bf_namelist_cls(
                    context, fds_label, fds_params)
                if bf_namelist_cls:
                    # This FDS namelists is managed:
                    # get element, instanciate and import BFNamelist
                    element = self._get_imported_element(
                        context, bf_namelist_cls, fds_label)
                    try:
                        bf_namelist_cls(element).from_fds(context, fds_params)
                    except BFException as err:
                        errors = True
                        free_texts.extend(err.free_texts)
                else:
                    # This FDS namelists is not managed
                    free_texts.append(fds_original)
        # Save free_texts, even if empty
        # (remember, bf_head_free_text is not set to default)
        self._save_imported_unmanaged_tokens(context, free_texts)
        # Return
        if errors:
            raise BFException(
                self, "Errors reported, see details in HEAD free text file.")


# Add methods to original Blender type

Scene.__str__ = BFScene.__str__
Scene.bf_namelists = BFScene.bf_namelists
Scene.set_default_appearance = BFScene.set_default_appearance

Scene._myself_to_fds = BFScene._myself_to_fds
Scene._header_to_fds = BFScene._header_to_fds
Scene._free_text_to_fds = BFScene._free_text_to_fds
Scene._children_to_fds = BFScene._children_to_fds
Scene.to_fds = BFScene.to_fds
Scene.to_ge1 = BFScene.to_ge1

Scene._get_imported_bf_namelist_cls = BFScene._get_imported_bf_namelist_cls
Scene._get_imported_element = BFScene._get_imported_element
Scene._save_imported_unmanaged_tokens = BFScene._save_imported_unmanaged_tokens
Scene.from_fds = BFScene.from_fds
