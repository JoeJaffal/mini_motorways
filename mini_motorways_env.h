#ifndef MINI_MOTORWAYS_ENV_H
#define MINI_MOTORWAYS_ENV_H

// added by Mohammad
#include <algorithm>
#include <cmath>
#include <string>
// stop


#include <GL/glew.h>
#include <GLFW/glfw3.h>
#include <glm/glm.hpp>
#include <glm/gtc/matrix_transform.hpp>
#include <glm/gtc/type_ptr.hpp>

#include <vector>
#include <memory>
#include <random>
#include <queue>
#include <unordered_map>
#include <unordered_set>
#include <chrono>
#include <iostream>
#include <fstream>
#include <sstream>

// Forward declarations
struct Car;
struct Building;
class Renderer;
class PathFinder;

enum class TileType : int {
    EMPTY = 0,
    HOUSE = 1,
    BUSINESS = 2,
    ROAD = 3,
    MOTORWAY = 4,
    BRIDGE = 5,
    ROUNDABOUT = 6,
    TRAFFIC_LIGHT = 7
};

enum class CarColor : int {
    RED = 0,
    BLUE = 1,
    GREEN = 2,
    YELLOW = 3,
    PURPLE = 4,
    ORANGE = 5
};

struct Position {
    int x, y;
    
    Position(int x = 0, int y = 0) : x(x), y(y) {}
    
    bool operator==(const Position& other) const {
        return x == other.x && y == other.y;
    }
    
    bool operator!=(const Position& other) const {
        return !(*this == other);
    }
};

// Hash function for Position
namespace std {
    template<>
    struct hash<Position> {
        size_t operator()(const Position& p) const {
            return hash<int>()(p.x) ^ (hash<int>()(p.y) << 1);
        }
    };
}

struct Car {
    Position position;
    Position destination;
    CarColor color;
    std::vector<Position> path;
    int stuck_time;
    bool completed;
    float visual_x, visual_y;  // For smooth animation
    float speed;
    
    Car(Position pos, Position dest, CarColor col) 
        : position(pos), destination(dest), color(col), stuck_time(0), 
          completed(false), visual_x(pos.x), visual_y(pos.y), speed(0.1f) {}
};

struct Building {
    Position position;
    CarColor color;
    TileType type;
    int cars_spawned;
    int max_cars;
    
    Building(Position pos, CarColor col, TileType t) 
        : position(pos), color(col), type(t), cars_spawned(0), max_cars(5) {}
};

class MiniMotorwaysEnvironment {
private:
    static const int GRID_WIDTH = 20;
    static const int GRID_HEIGHT = 20;
    static const int MAX_STEPS = 1000;
    
    // Game state
    std::vector<std::vector<TileType>> grid;
    std::vector<std::shared_ptr<Car>> cars;
    std::vector<Building> buildings;
    std::unordered_map<std::string, int> resources;
    
    // Game metrics
    int score;
    int current_step;
    bool game_over;
    int congestion_penalty;
    
    // OpenGL components
    GLFWwindow* window;
    std::unique_ptr<Renderer> renderer;
    std::unique_ptr<PathFinder> pathfinder;
    
    // Random number generation
    std::mt19937 rng;
    std::uniform_int_distribution<int> position_dist_x;
    std::uniform_int_distribution<int> position_dist_y;
    std::uniform_real_distribution<float> spawn_dist;

public:
    MiniMotorwaysEnvironment();
    ~MiniMotorwaysEnvironment();
    
    // Core RL interface
    bool initialize();
    std::vector<float> reset();
    std::vector<float> step(const std::vector<int>& action);
    std::vector<float> get_observation() const;
    bool is_done() const;
    void render();
    void close();
    
    // Game mechanics
    bool execute_action(int action_type, int x, int y);
    void simulate_traffic();
    void spawn_cars();
    bool check_game_over();
    
    // Utility functions
    Position find_empty_position();
    bool is_valid_position(const Position& pos) const;
    bool can_move_to(const Position& pos) const;
    void spawn_initial_buildings();
    
    // Getters for RL training
    int get_score() const { return score; }
    int get_step() const { return current_step; }
    int get_car_count() const { return cars.size(); }
    bool should_close() const;
    
    // Getters for renderer access
    const std::vector<std::vector<TileType>>& get_grid() const { return grid; }
    const std::vector<Building>& get_buildings() const { return buildings; }
    const std::vector<std::shared_ptr<Car>>& get_cars() const { return cars; }
    const std::unordered_map<std::string, int>& get_resources() const { return resources; }
};

class Renderer {
private:
    GLuint shader_program;
    GLuint vao, vbo;
    glm::mat4 projection;
    glm::mat4 view;
    
    // Color definitions
    std::unordered_map<TileType, glm::vec3> tile_colors;
    std::unordered_map<CarColor, glm::vec3> car_colors;

public:
    Renderer();
    ~Renderer();
    
    bool initialize();
    void render_frame(const MiniMotorwaysEnvironment& env);
    void render_grid(const std::vector<std::vector<TileType>>& grid);
    void render_buildings(const std::vector<Building>& buildings);
    void render_cars(const std::vector<std::shared_ptr<Car>>& cars);
    void render_ui(int score, int step, const std::unordered_map<std::string, int>& resources);
    
private:
    GLuint load_shader(const std::string& vertex_src, const std::string& fragment_src);
    void setup_quad();
};

class PathFinder {
private:
    struct Node {
        Position pos;
        int g_cost, h_cost;
        Position parent;
        
        int f_cost() const { return g_cost + h_cost; }
    };
    
    int calculate_distance(const Position& a, const Position& b) const;
    std::vector<Position> reconstruct_path(const std::unordered_map<Position, Position>& came_from,
                                         const Position& start, const Position& goal) const;

public:
    std::vector<Position> find_path(const Position& start, const Position& goal,
                                  const std::vector<std::vector<TileType>>& grid) const;
};

#endif // MINI_MOTORWAYS_ENV_H