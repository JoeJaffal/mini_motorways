#include "mini_motorways_env.h"

// MiniMotorwaysEnvironment Implementation
MiniMotorwaysEnvironment::MiniMotorwaysEnvironment() 
    : grid(GRID_HEIGHT, std::vector<TileType>(GRID_WIDTH, TileType::EMPTY)),
      score(0), current_step(0), game_over(false), congestion_penalty(0),
      window(nullptr), rng(std::chrono::steady_clock::now().time_since_epoch().count()),
      position_dist_x(0, GRID_WIDTH - 1), position_dist_y(0, GRID_HEIGHT - 1),
      spawn_dist(0.0f, 1.0f) {
    
    construction_cost = 0;
    
    renderer = std::make_unique<Renderer>();
    pathfinder = std::make_unique<PathFinder>();
}

MiniMotorwaysEnvironment::~MiniMotorwaysEnvironment() {
    close();
}

bool MiniMotorwaysEnvironment::initialize() {
    // Initialize GLFW
    if (!glfwInit()) {
        std::cerr << "Failed to initialize GLFW" << std::endl;
        return false;
    }
    
    // Set OpenGL version (3.3 Core)
    glfwWindowHint(GLFW_SAMPLES, 4);
    glfwWindowHint(GLFW_CONTEXT_VERSION_MAJOR, 3);
    glfwWindowHint(GLFW_CONTEXT_VERSION_MINOR, 3);
    glfwWindowHint(GLFW_OPENGL_PROFILE, GLFW_OPENGL_CORE_PROFILE);
    glfwWindowHint(GLFW_OPENGL_FORWARD_COMPAT, GL_TRUE); // Required on Mac
    
    // Create window
    window = glfwCreateWindow(1200, 800, "Mini Motorways RL", nullptr, nullptr);
    if (!window) {
        std::cerr << "Failed to create GLFW window" << std::endl;
        glfwTerminate();
        return false;
    }
    
    glfwMakeContextCurrent(window);
    
    // Initialize GLEW
    if (glewInit() != GLEW_OK) {
        std::cerr << "Failed to initialize GLEW" << std::endl;
        return false;
    }
    
    // Initialize renderer
    if (!renderer->initialize()) {
        std::cerr << "Failed to initialize renderer" << std::endl;
        return false;
    }
    
    // Set viewport
    glViewport(0, 0, 1200, 800);
    glEnable(GL_MULTISAMPLE);
    glEnable(GL_BLEND);
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
    
    return true;
}

std::vector<float> MiniMotorwaysEnvironment::reset() {
    // Reset game state
    grid.assign(GRID_HEIGHT, std::vector<TileType>(GRID_WIDTH, TileType::EMPTY));
    cars.clear();
    buildings.clear();
    
    score = 0;
    current_step = 0;
    game_over = false;
    congestion_penalty = 0;
    
    construction_cost = 0;
    
    // Spawn initial buildings
    spawn_initial_buildings();
    
    return get_observation();
}

std::vector<float> MiniMotorwaysEnvironment::step(const std::vector<int>& action) {
    if (game_over || action.size() != 3) {
        return get_observation();
    }
    
    current_step++;
    
    // Execute action
    if (action[0] >= 0 && action[0] < 5) {  // Infrastructure action
        execute_action(action[0], action[1], action[2]);
    }
    
    // Simulate traffic
    simulate_traffic();
    
    // Spawn new cars
    spawn_cars();
    
    // Check game over
    game_over = check_game_over();
    
    return get_observation();
}

bool MiniMotorwaysEnvironment::execute_action(int action_type, int x, int y) {
    if (!is_valid_position(Position(x, y))) return false;
    TileType tile;
    int cost;
    switch (action_type) {
        case 0: tile = TileType::ROAD; cost = 1; break;
        case 1: tile = TileType::BRIDGE; cost = 10; break;
        case 2: tile = TileType::ROUNDABOUT; cost = 8; break;
        case 3: tile = TileType::TRAFFIC_LIGHT; cost = 5; break;
        case 4:
            if (grid[y][x] != TileType::ROAD && grid[y][x] != TileType::BRIDGE &&
                grid[y][x] != TileType::ROUNDABOUT && grid[y][x] != TileType::TRAFFIC_LIGHT)
                return false;
            grid[y][x] = TileType::EMPTY;
            // Spending is cumulative; demolition does not refund previous costs.
            for (auto& car : cars) car->path.clear();
            return true;
        default: return false;
    }
    // A light costs 5 additional points and requires an existing road.
    const TileType required = action_type == 3 ? TileType::ROAD : TileType::EMPTY;
    if (grid[y][x] != required) return false;
    grid[y][x] = tile;
    construction_cost += cost;
    for (auto& car : cars) car->path.clear();
    return true;
}
void MiniMotorwaysEnvironment::simulate_traffic() {
    std::vector<std::shared_ptr<Car>> completed_cars;
    
    for (auto& car : cars) {
        if (car->completed) continue;
        
        // Find path if needed
        if (car->path.empty()) {
            car->path = pathfinder->find_path(car->position, car->destination, grid);
        }
        
        // Move car along path
        if (!car->path.empty() && car->path.size() > 1) {
            Position next_pos = car->path[1];
            
            if (can_move_to(next_pos)) {
                car->position = next_pos;
                car->path.erase(car->path.begin());
                car->stuck_time = 0;
                
                // Update visual position for smooth animation
                car->visual_x += (next_pos.x - car->visual_x) * car->speed;
                car->visual_y += (next_pos.y - car->visual_y) * car->speed;
                
                // Check if reached destination
                if (car->position == car->destination) {
                    car->completed = true;
                    completed_cars.push_back(car);
                    score++;
                }
            } else {
                car->stuck_time++;
                if (car->stuck_time > 10) {
                    congestion_penalty++;
                }
            }
        }
    }
    
    // Remove completed cars
    cars.erase(std::remove_if(cars.begin(), cars.end(),
                             [](const std::shared_ptr<Car>& car) { return car->completed; }),
               cars.end());
}

void MiniMotorwaysEnvironment::spawn_cars() {
    if (current_step % 5 == 0) {  // Spawn every 5 steps
        for (auto& building : buildings) {
            if (building.type == TileType::HOUSE && 
                building.cars_spawned < building.max_cars && 
                spawn_dist(rng) < 0.3f) {
                
                // Find matching business
                for (const auto& business : buildings) {
                    if (business.type == TileType::BUSINESS && 
                        business.color == building.color) {
                        
                        auto car = std::make_shared<Car>(
                            building.position, business.position, building.color);
                        cars.push_back(car);
                        building.cars_spawned++;
                        break;
                    }
                }
            }
        }
    }
}

void MiniMotorwaysEnvironment::spawn_initial_buildings() {
    std::vector<CarColor> colors = {CarColor::RED, CarColor::BLUE, CarColor::GREEN};
    
    // Spawn houses
    for (int i = 0; i < 3; i++) {
        Position pos = find_empty_position();
        if (pos.x != -1) {
            buildings.emplace_back(pos, colors[i], TileType::HOUSE);
            grid[pos.y][pos.x] = TileType::HOUSE;
        }
    }
    
    // Spawn businesses
    for (int i = 0; i < 2; i++) {
        Position pos = find_empty_position();
        if (pos.x != -1) {
            buildings.emplace_back(pos, colors[i], TileType::BUSINESS);
            grid[pos.y][pos.x] = TileType::BUSINESS;
        }
    }
}

Position MiniMotorwaysEnvironment::find_empty_position() {
    for (int attempts = 0; attempts < 100; attempts++) {
        int x = position_dist_x(rng);
        int y = position_dist_y(rng);
        if (grid[y][x] == TileType::EMPTY) {
            return Position(x, y);
        }
    }
    return Position(-1, -1);  // No empty position found
}

bool MiniMotorwaysEnvironment::is_valid_position(const Position& pos) const {
    return pos.x >= 0 && pos.x < GRID_WIDTH && pos.y >= 0 && pos.y < GRID_HEIGHT;
}

bool MiniMotorwaysEnvironment::can_move_to(const Position& pos) const {
    if (!is_valid_position(pos)) return false;
    
    TileType tile = grid[pos.y][pos.x];
    return tile == TileType::ROAD ||
           tile == TileType::BRIDGE || tile == TileType::ROUNDABOUT ||
           tile == TileType::TRAFFIC_LIGHT || tile == TileType::HOUSE || 
           tile == TileType::BUSINESS;
}

bool MiniMotorwaysEnvironment::check_game_over() {
    // Count stuck cars
    int stuck_cars = 0;
    for (const auto& car : cars) {
        if (car->stuck_time > 20) stuck_cars++;
    }
    
    if (stuck_cars > 10) return true;
    
    if (current_step >= MAX_STEPS) return true;
    
    return false;
}

std::vector<float> MiniMotorwaysEnvironment::get_observation() const {
    std::vector<float> observation;
    
    // Flatten grid (20x20 = 400 values)
    for (int y = 0; y < GRID_HEIGHT; y++) {
        for (int x = 0; x < GRID_WIDTH; x++) {
            observation.push_back(static_cast<float>(static_cast<int>(grid[y][x])) / 6.0f);
        }
    }
    
    // Car density layer (20x20 = 400 values)
    std::vector<std::vector<int>> car_density(GRID_HEIGHT, std::vector<int>(GRID_WIDTH, 0));
    for (const auto& car : cars) {
        if (car->position.x >= 0 && car->position.x < GRID_WIDTH &&
            car->position.y >= 0 && car->position.y < GRID_HEIGHT) {
            car_density[car->position.y][car->position.x]++;
        }
    }
    
    for (int y = 0; y < GRID_HEIGHT; y++) {
        for (int x = 0; x < GRID_WIDTH; x++) {
            observation.push_back(std::min(car_density[y][x] / 5.0f, 1.0f));
        }
    }
    
    // Spending (1 value, scaled but not capped).
    observation.push_back(construction_cost / 100.0f);

    // Game stats (4 values)
    observation.push_back(score / 100.0f);  // Normalize score
    observation.push_back(cars.size() / 50.0f);  // Normalize car count
    observation.push_back(congestion_penalty / 100.0f);  // Normalize congestion
    observation.push_back(current_step / static_cast<float>(MAX_STEPS));
    
    return observation;
}

void MiniMotorwaysEnvironment::render() {
    if (!window) return;
    
    int framebuffer_width, framebuffer_height;
    glfwGetFramebufferSize(window, &framebuffer_width, &framebuffer_height);
    glViewport(0, 0, framebuffer_width, framebuffer_height);
    glClear(GL_COLOR_BUFFER_BIT);
    glClearColor(0.1f, 0.1f, 0.1f, 1.0f);
    
    renderer->render_frame(*this);
    
    const std::string title = "Mini Motorways | Score: " + std::to_string(score) +
        " | Construction spent: " + std::to_string(construction_cost) + " points";
    glfwSetWindowTitle(window, title.c_str());
    glfwSwapBuffers(window);
    glfwPollEvents();
}

bool MiniMotorwaysEnvironment::should_close() const {
    return window && glfwWindowShouldClose(window);
}

bool MiniMotorwaysEnvironment::is_done() const {
    return game_over || should_close();
}

void MiniMotorwaysEnvironment::close() {
    if (window) {
        glfwDestroyWindow(window);
        window = nullptr;
    }
    glfwTerminate();
}

// PathFinder Implementation
std::vector<Position> PathFinder::find_path(const Position& start, const Position& goal,
                                          const std::vector<std::vector<TileType>>& grid) const {
    
    // Comparator for priority queue
    struct NodeComparator {
        bool operator()(const Node& a, const Node& b) const {
            return a.f_cost() > b.f_cost();
        }
    };
    
    std::priority_queue<Node, std::vector<Node>, NodeComparator> open_set;
    std::unordered_set<Position> closed_set;
    std::unordered_map<Position, Position> came_from;
    std::unordered_map<Position, int> g_score;
    
    Node start_node;
    start_node.pos = start;
    start_node.g_cost = 0;
    start_node.h_cost = calculate_distance(start, goal);
    
    open_set.push(start_node);
    g_score[start] = 0;
    
    std::vector<Position> directions = {{0, 1}, {1, 0}, {0, -1}, {-1, 0}};
    
    while (!open_set.empty()) {
        Node current = open_set.top();
        open_set.pop();
        
        if (current.pos == goal) {
            return reconstruct_path(came_from, start, goal);
        }
        
        closed_set.insert(current.pos);
        
        for (const auto& dir : directions) {
            Position neighbor(current.pos.x + dir.x, current.pos.y + dir.y);
            
            if (neighbor.x < 0 || neighbor.x >= grid[0].size() ||
                neighbor.y < 0 || neighbor.y >= grid.size()) continue;
            
            if (closed_set.count(neighbor)) continue;
            
            // Check if tile is passable
            TileType tile = grid[neighbor.y][neighbor.x];
            bool passable = (tile == TileType::ROAD ||
                           tile == TileType::BRIDGE || tile == TileType::ROUNDABOUT ||
                           tile == TileType::TRAFFIC_LIGHT || tile == TileType::HOUSE || 
                           tile == TileType::BUSINESS);
            
            if (!passable) continue;
            
            int tentative_g = g_score[current.pos] + 1;
            
            if (g_score.find(neighbor) == g_score.end() || tentative_g < g_score[neighbor]) {
                came_from[neighbor] = current.pos;
                g_score[neighbor] = tentative_g;
                
                Node neighbor_node;
                neighbor_node.pos = neighbor;
                neighbor_node.g_cost = tentative_g;
                neighbor_node.h_cost = calculate_distance(neighbor, goal);
                neighbor_node.parent = current.pos;
                
                open_set.push(neighbor_node);
            }
        }
    }
    
    return {};  // No path found
}

int PathFinder::calculate_distance(const Position& a, const Position& b) const {
    return abs(a.x - b.x) + abs(a.y - b.y);  // Manhattan distance
}

std::vector<Position> PathFinder::reconstruct_path(
    const std::unordered_map<Position, Position>& came_from,
    const Position& start, const Position& goal) const {
    
    std::vector<Position> path;
    Position current = goal;
    
    while (current != start) {
        path.push_back(current);
        auto it = came_from.find(current);
        if (it == came_from.end()) break;
        current = it->second;
    }
    
    path.push_back(start);
    std::reverse(path.begin(), path.end());
    return path;
}
