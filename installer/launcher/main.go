// NaijaTel Impayés AI — lanceur autonome, zéro dépendance.
// Compile une fois, s'exécute partout : Windows, Linux, macOS — sans Python, sans Docker, sans réseau.
//   go build -ldflags="-s -w" -o NaijaTel-ImpayesAI-Demo[.exe] .
// Sert la démo sur un port éphémère 127.0.0.1 et ouvre le navigateur par défaut.
package main

import (
	"embed"
	"fmt"
	"io/fs"
	"log"
	"net"
	"net/http"
	"os"
	"os/exec"
	"os/signal"
	"runtime"
	"syscall"
)

//go:embed assets
var embedded embed.FS

func main() {
	ui, err := fs.Sub(embedded, "assets")
	if err != nil {
		log.Fatal("assets embarqués introuvables :", err)
	}

	// Port éphémère sur loopback uniquement : aucune exposition réseau.
	listener, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		log.Fatal(err)
	}
	port := listener.Addr().(*net.TCPAddr).Port
	url := fmt.Sprintf("http://127.0.0.1:%d/", port)

	fmt.Printf("NaijaTel Impayés AI — démo disponible sur %s (Ctrl+C pour quitter)\n", url)

	// Ouvre le navigateur par défaut, sans dépendance externe.
	go openBrowser(url)

	mux := http.NewServeMux()
	mux.Handle("/", http.FileServer(http.FS(ui)))
	server := &http.Server{Handler: securityHeaders(mux)}

	// Arrêt propre sur Ctrl+C (Windows n'a pas toujours SIGINT).
	go func() {
		ch := make(chan os.Signal, 2)
		signal.Notify(ch, syscall.SIGINT, syscall.SIGTERM)
		<-ch
		fmt.Println("\nArrêt — merci d'avoir essayé Impayés AI.")
		server.Close()
	}()
	if err := server.Serve(listener); err != http.ErrServerClosed {
		log.Fatal(err)
	}
}

func securityHeaders(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("X-Content-Type-Options", "nosniff")
		w.Header().Set("X-Frame-Options", "DENY")
		w.Header().Set("Cache-Control", "no-store")
		next.ServeHTTP(w, r)
	})
}

func openBrowser(url string) {
	var cmd *exec.Cmd
	switch runtime.GOOS {
	case "windows":
		cmd = exec.Command("rundll32", "url.dll,FileProtocolHandler", url)
	case "darwin":
		cmd = exec.Command("open", url)
	default: // linux, bsd…
		cmd = exec.Command("xdg-open", url)
	}
	_ = cmd.Start()
}
