package main

import (
	"context"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/joho/godotenv"
	"github.com/rs/zerolog"
	zlog "github.com/rs/zerolog/log"
)

type Config struct {
	Port        string
	Host        string
	Environment string
	CORSOrigins string
}

func loadConfig() *Config {
	// Load .env file
	if err := godotenv.Load(); err != nil {
		zlog.Warn().Msg("No .env file found")
	}

	return &Config{
		Port:        getEnv("API_PORT", "8080"),
		Host:        getEnv("API_HOST", "0.0.0.0"),
		Environment: getEnv("GO_ENV", "development"),
		CORSOrigins: getEnv("CORS_ORIGINS", "http://localhost:3000"),
	}
}

func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}

func setupRouter(config *Config) *gin.Engine {
	// Set Gin mode
	if config.Environment == "production" {
		gin.SetMode(gin.ReleaseMode)
	}

	router := gin.New()

	// Middleware
	router.Use(gin.Logger())
	router.Use(gin.Recovery())

	// CORS middleware
	router.Use(func(c *gin.Context) {
		c.Header("Access-Control-Allow-Origin", config.CORSOrigins)
		c.Header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
		c.Header("Access-Control-Allow-Headers", "Content-Type, Authorization")
		
		if c.Request.Method == "OPTIONS" {
			c.AbortWithStatus(204)
			return
		}
		
		c.Next()
	})

	// Routes
	setupRoutes(router)

	return router
}

func setupRoutes(router *gin.Engine) {
	// Health check
	router.GET("/health", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{
			"status":  "healthy",
			"service": "News AI - API Gateway",
			"version": "1.0.0",
			"time":    time.Now().UTC(),
		})
	})

	// Root endpoint
	router.GET("/", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{
			"service":     "News AI - API Gateway",
			"version":     "1.0.0",
			"description": "High-performance API gateway for news analysis",
			"endpoints": gin.H{
				"health":     "/health",
				"headlines":  "/api/headlines",
				"events":     "/api/events", 
				"search":     "/api/search",
				"metrics":    "/api/metrics",
				"docs":       "/docs",
			},
		})
	})

	// API routes group
	api := router.Group("/api")
	{
		// Headlines endpoints
		api.GET("/headlines", getHeadlines)
		api.GET("/headlines/search", searchHeadlines)
		api.GET("/headlines/topics", getTopicStatistics)

		// Events endpoints
		api.GET("/events", getEvents)
		api.GET("/events/:id", getEventDetails)

		// Metrics endpoints
		api.GET("/metrics", getMetrics)
		api.GET("/topics/underrepresentation", getUnderrepresentationMetrics)

		// Vector database info
		api.GET("/vector-db-info", getVectorDBInfo)
	}
}

// Mock handlers - replace with actual implementations
func getHeadlines(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{
		"headlines": []gin.H{
			{
				"id":          "1",
				"title":       "Breaking: Tech Innovation Advances",
				"description": "Latest developments in technology sector",
				"url":         "https://example.com/news/1",
				"source":      "TechNews",
				"publishedAt": time.Now().UTC(),
				"topics":      []string{"technology", "business"},
			},
		},
		"total": 1,
		"note":  "Mock data from Go API service",
	})
}

func searchHeadlines(c *gin.Context) {
	query := c.Query("q")
	c.JSON(http.StatusOK, gin.H{
		"query":   query,
		"results": []gin.H{},
		"total":   0,
		"note":    "Search functionality to be implemented",
	})
}

func getTopicStatistics(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{
		"topics": gin.H{
			"technology": gin.H{"count": 45, "percentage": 25.5},
			"politics":   gin.H{"count": 38, "percentage": 21.6},
			"business":   gin.H{"count": 32, "percentage": 18.2},
			"science":    gin.H{"count": 28, "percentage": 15.9},
			"world":      gin.H{"count": 33, "percentage": 18.8},
		},
		"total": 176,
		"note":  "Mock topic statistics",
	})
}

func getEvents(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{
		"events": []gin.H{},
		"total":  0,
		"note":   "Event extraction to be implemented",
	})
}

func getEventDetails(c *gin.Context) {
	id := c.Param("id")
	c.JSON(http.StatusOK, gin.H{
		"id":   id,
		"note": "Event details to be implemented",
	})
}

func getMetrics(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{
		"metrics": gin.H{
			"headlines_processed": 1250,
			"classifications":     1180,
			"translations":        420,
			"events_extracted":    95,
			"uptime":             "2h 15m",
		},
		"note": "Mock system metrics",
	})
}

func getUnderrepresentationMetrics(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{
		"underrepresented_topics": []gin.H{
			{"topic": "art", "representation": 2.1, "target": 8.0},
			{"topic": "education", "representation": 4.5, "target": 10.0},
		},
		"note": "Mock underrepresentation analysis",
	})
}

func getVectorDBInfo(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{
		"status":     "connected",
		"collection": "news_embeddings",
		"vectors":    1180,
		"dimension":  384,
		"note":       "Mock vector database status",
	})
}

func main() {
	// Setup logging
	zerolog.TimeFieldFormat = zerolog.TimeFormatUnix
	zlog.Logger = zlog.Output(zerolog.ConsoleWriter{Out: os.Stderr})

	// Load configuration
	config := loadConfig()

	zlog.Info().
		Str("host", config.Host).
		Str("port", config.Port).
		Str("env", config.Environment).
		Msg("Starting News AI API Gateway")

	// Setup router
	router := setupRouter(config)

	// Setup server
	srv := &http.Server{
		Addr:    fmt.Sprintf("%s:%s", config.Host, config.Port),
		Handler: router,
	}

	// Start server in a goroutine
	go func() {
		zlog.Info().Msgf("Server starting on %s", srv.Addr)
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("Failed to start server: %v", err)
		}
	}()

	// Wait for interrupt signal to gracefully shutdown
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	zlog.Info().Msg("Shutting down server...")

	// Graceful shutdown with timeout
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	if err := srv.Shutdown(ctx); err != nil {
		zlog.Fatal().Err(err).Msg("Server forced to shutdown")
	}

	zlog.Info().Msg("Server exited")
} 