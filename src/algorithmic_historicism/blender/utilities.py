from __future__ import annotations


def linked_duplicate_snippet(source_object_name: str, new_object_name: str) -> str:
    return f'''
source = bpy.data.objects["{source_object_name}"]
copy = source.copy()
copy.data = source.data
copy.name = "{new_object_name}"
bpy.context.collection.objects.link(copy)
'''
