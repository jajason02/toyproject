import { CanvasTexture, LinearFilter, SRGBColorSpace } from 'three'

const sharedSpineTexturePromises = new Map()

function getOpaqueBounds(context, width, height) {
  const pixels = context.getImageData(0, 0, width, height).data
  let minX = width
  let minY = height
  let maxX = 0
  let maxY = 0

  for (let y = 0; y < height; y += 2) {
    for (let x = 0; x < width; x += 2) {
      const alpha = pixels[(y * width + x) * 4 + 3]
      if (alpha > 24) {
        minX = Math.min(minX, x)
        minY = Math.min(minY, y)
        maxX = Math.max(maxX, x)
        maxY = Math.max(maxY, y)
      }
    }
  }

  return {
    x: minX,
    y: minY,
    width: Math.max(1, maxX - minX),
    height: Math.max(1, maxY - minY),
  }
}

async function createSharedSpineTexture(spineNumber) {
  const canvas = document.createElement('canvas')
  canvas.width = 1024
  canvas.height = 2048

  const context = canvas.getContext('2d')
  let imageLoaded = false

  try {
    const response = await fetch(`/image/book_spine_tight${spineNumber}.png`)
    if (response.ok) {
      const image = await createImageBitmap(await response.blob())
      const sourceCanvas = document.createElement('canvas')
      sourceCanvas.width = image.width
      sourceCanvas.height = image.height
      const sourceContext = sourceCanvas.getContext('2d')
      sourceContext.drawImage(image, 0, 0)
      const bounds = getOpaqueBounds(
        sourceContext,
        sourceCanvas.width,
        sourceCanvas.height,
      )
      context.drawImage(
        image,
        bounds.x,
        bounds.y,
        bounds.width,
        bounds.height,
        0,
        0,
        canvas.width,
        canvas.height,
      )
      image.close()
      imageLoaded = true
    }
  } catch {
    imageLoaded = false
  }

  if (!imageLoaded) {
    context.fillStyle = '#76553b'
    context.fillRect(0, 0, canvas.width, canvas.height)
  }

  const texture = new CanvasTexture(canvas)
  texture.colorSpace = SRGBColorSpace
  texture.anisotropy = 16
  texture.generateMipmaps = false
  texture.minFilter = LinearFilter
  texture.magFilter = LinearFilter
  return texture
}

export function getSharedSpineTexture(bookId) {
  const spineNumber = (Math.abs(Number(bookId) || 0) % 5) + 1

  if (!sharedSpineTexturePromises.has(spineNumber)) {
    const promise = createSharedSpineTexture(spineNumber).catch((error) => {
      sharedSpineTexturePromises.delete(spineNumber)
      throw error
    })
    sharedSpineTexturePromises.set(spineNumber, promise)
  }

  return sharedSpineTexturePromises.get(spineNumber)
}
