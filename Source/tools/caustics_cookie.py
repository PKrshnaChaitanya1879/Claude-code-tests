"""A tileable caustic pattern for the sun's light cookie (M3), made the physical way: photons on a
grid are refracted by a random (tileable, FFT-filtered) wave height field and splatted where they land
on the sea floor; their pile-up is the bright web. Writes Assets/Verne/Textures/caustics_cookie.png."""
import numpy as np, sys
from PIL import Image, ImageFilter
N = 512
rng = np.random.default_rng(5)
k = np.fft.fftfreq(N)[:, None] ** 2 + np.fft.fftfreq(N)[None, :] ** 2
spec = (rng.normal(size=(N, N)) + 1j * rng.normal(size=(N, N))) * np.exp(-k * 900) * (k > 0)
h = np.real(np.fft.ifft2(spec)); h /= h.std()
gy, gx = np.gradient(h)
acc = np.zeros((N, N))
S = 2  # photons per pixel per axis
for oy in range(S):
    for ox in range(S):
        yy, xx = np.mgrid[0:N, 0:N].astype(float)
        yy += oy / S; xx += ox / S
        ty = (yy + gy * 38.0).astype(int) % N; tx = (xx + gx * 38.0).astype(int) % N
        np.add.at(acc, (ty, tx), 1.0)
acc /= acc.mean()
img = Image.fromarray(np.clip(acc * 70, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.1))
a = np.asarray(img).astype(float) / 255.0
a = 0.35 + 0.65 * np.clip(a / np.percentile(a, 99.5), 0, 1) ** 0.8          # never fully dark: a cookie dims the light, it doesn't kill it
Image.fromarray((a * 255).astype(np.uint8)).save(sys.argv[1] if len(sys.argv) > 1 else 'caustics_cookie.png')
print('ok', a.min(), a.max(), a.mean())
