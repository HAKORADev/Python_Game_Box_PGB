# PGB Web Games — v0.1.0

The first web-based addition to the Python Game Box collection. Built with Next.js, React Three Fiber, and Tailwind CSS.

## Games

| Game | Version | Screenshot |
|------|---------|------------|
| 🐍 **3D Snake** | v0.1.0 | ![3D Snake](../../assets/snake3d-0.1.0.png) |

> 📸 **[View all screenshots →](../../showcase.md)**

## How to Run Locally

1. Install [Node.js](https://nodejs.org/) (v18+)
2. Navigate to the game folder: `cd src/web/v0.1.0/Snake3D/`
3. Install dependencies: `npm install`
4. Start dev server: `npm run dev`
5. Open [http://localhost:3000](http://localhost:3000)

> Requires a modern browser with WebGL 2 support (Chrome, Firefox, Edge, Safari).

## Folder Structure

```
src/web/v0.1.0/
├── Snake3D/              # 3D Snake game (Next.js + Three.js)
├── readme.md             # This file
├── about.txt             # About this version
├── controls.txt          # Controls reference
└── changelog.txt         # Version history
```

## Technology Stack

- **Framework**: Next.js 16 (React 19)
- **3D Engine**: Three.js + React Three Fiber
- **Styling**: Tailwind CSS 4 + shadcn/ui
- **State**: Zustand
- **Post-Processing**: @react-three/postprocessing (volumetric god rays)

## Browser Support

Requires a modern browser with WebGL 2 support (Chrome, Firefox, Edge, Safari).
