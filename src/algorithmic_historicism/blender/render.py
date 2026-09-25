from __future__ import annotations


def deterministic_render_settings_snippet(output_path: str) -> str:
    return f'''
scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 1024
scene.render.resolution_y = 1024
scene.render.film_transparent = False
scene.render.filepath = r"{output_path}"
'''
