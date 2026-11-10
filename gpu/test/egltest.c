// Minimal EGL/GLES2 smoke test for Mesa panfrost on Android: pbuffer, clear, readback.
#include <EGL/egl.h>
#include <GLES2/gl2.h>
#include <stdio.h>
#include <time.h>

static double now(void) {
   struct timespec ts;
   clock_gettime(CLOCK_MONOTONIC, &ts);
   return ts.tv_sec + ts.tv_nsec / 1e9;
}

int main(void) {
   EGLDisplay d = eglGetDisplay(EGL_DEFAULT_DISPLAY);
   EGLint maj, min;
   if (!eglInitialize(d, &maj, &min)) { printf("eglInitialize failed 0x%x\n", eglGetError()); return 1; }
   printf("EGL %d.%d vendor=%s\n", maj, min, eglQueryString(d, EGL_VENDOR));
   EGLint cfg_attr[] = { EGL_SURFACE_TYPE, EGL_PBUFFER_BIT, EGL_RENDERABLE_TYPE, EGL_OPENGL_ES2_BIT,
                         EGL_RED_SIZE, 8, EGL_GREEN_SIZE, 8, EGL_BLUE_SIZE, 8, EGL_ALPHA_SIZE, 8, EGL_NONE };
   EGLConfig cfg; EGLint n = 0;
   if (!eglChooseConfig(d, cfg_attr, &cfg, 1, &n) || n < 1) { printf("no config 0x%x\n", eglGetError()); return 1; }
   EGLint pb_attr[] = { EGL_WIDTH, 256, EGL_HEIGHT, 256, EGL_NONE };
   EGLSurface s = eglCreatePbufferSurface(d, cfg, pb_attr);
   EGLint ctx_attr[] = { EGL_CONTEXT_CLIENT_VERSION, 2, EGL_NONE };
   EGLContext c = eglCreateContext(d, cfg, EGL_NO_CONTEXT, ctx_attr);
   if (s == EGL_NO_SURFACE || c == EGL_NO_CONTEXT || !eglMakeCurrent(d, s, s, c)) {
      printf("surface/context failed 0x%x\n", eglGetError()); return 1;
   }
   printf("GL_VENDOR=%s\nGL_RENDERER=%s\nGL_VERSION=%s\n", glGetString(GL_VENDOR), glGetString(GL_RENDERER), glGetString(GL_VERSION));
   double t0 = now();
   for (int i = 0; i < 100; i++) {
      glClearColor((i & 1) ? 1.0f : 0.0f, 0.5f, 0.25f, 1.0f);
      glClear(GL_COLOR_BUFFER_BIT);
      glFlush();
   }
   unsigned char px[4] = {0};
   glReadPixels(10, 10, 1, 1, GL_RGBA, GL_UNSIGNED_BYTE, px);
   printf("100 clears + readback: %.1f ms, pixel = %d %d %d %d (expect 255 127/128 63/64 255)\n",
          (now() - t0) * 1e3, px[0], px[1], px[2], px[3]);
   eglTerminate(d);
   return 0;
}
