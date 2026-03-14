import { defineConfig } from 'vite'

export default defineConfig({
  root: '.',
  build: {
    outDir: 'dist',
    rollupOptions: {
      input: {
        main: 'index.html',
        restaurant_login: 'restaurant_login.html',
        centre_login: 'centre_login.html',
        restaurant_register: 'restaurant_register.html',
        centre_register: 'centre_register.html',
        restaurant_dashboard: 'restaurant_dashboard.html',
        centre_dashboard: 'centre_dashboard.html'
      }
    }
  }
})
