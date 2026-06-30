# Arctic Bookshelf 3D Model Pack

Purpose: a tall, clean, warm library-style bookshelf matching the uploaded Arctic site UI.

Files:
- arctic_tall_empty_bookshelf.glb: empty 4-compartment bookshelf, no props/books.
- arctic_tall_bookshelf_with_bottom_props.glb: same bookshelf with detachable bottom-tier props.
- arctic_bottom_props_pack.glb: props only.
- arctic_props_individual/: each prop as a separate GLB.
- arctic_bookshelf_attach_points.json: shelf coordinate slots for procedural book placement.
- arctic_props_manifest.json: prop prefixes and anchors.
- arctic_bookshelf_validation_report.json: automated design checks.

TresJS tips:
- Put GLB files into public/models/.
- Load with GLTFModel or useGLTF.
- Every detachable prop node starts with `prop_`.
- Optional shelf lights start with `optional_`.
- Bottom tier is reserved for props by default; tiers 2-4 are clean book placement zones.

Example hide props:
```js
gltf.scene.traverse((obj) => {
  if (obj.name?.startsWith('prop_')) obj.visible = false
})
```

Example hide optional lights:
```js
gltf.scene.traverse((obj) => {
  if (obj.name?.startsWith('optional_')) obj.visible = false
})
```

Validation status: PASS
