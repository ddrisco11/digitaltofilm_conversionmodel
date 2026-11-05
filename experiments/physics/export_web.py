"""Sample the four observable stages of the fixed spectral process on a 65³ sRGB grid."""
from simulation import HERE, CameraAndPrinter, np, srgb

def stage_views(sim, rgb):
    exposure, dyes, transmission, _, _, xyz = sim.stages(rgb)
    return {
        "exposure": (np.log10(exposure + 1e-10) + 3) / 4,
        "dyes": dyes / sim.film["curves"].max(axis=0),
        "negative": srgb((transmission @ sim.observer) @ sim.to_rgb),
        "print": srgb(xyz @ sim.to_rgb),
    }

if __name__ == "__main__":
    destination = HERE.parents[1] / "docs/physics"
    axis = np.linspace(0, 1, 65)
    blue, green, red = np.meshgrid(axis, axis, axis, indexing="ij")
    grid = np.column_stack([red.ravel(), green.ravel(), blue.ravel()])
    sim = CameraAndPrinter()
    tables = {}
    for i in range(0, len(grid), 4096):
        for stage, values in stage_views(sim, grid[i:i+4096]).items():
            tables.setdefault(stage, []).append(np.rint(255*np.clip(values,0,1)).astype("uint8"))
    for stage, chunks in tables.items():
        np.concatenate(chunks).tofile(destination / (stage + ".bin"))
