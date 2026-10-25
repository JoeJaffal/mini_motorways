#include "mini_motorways_env.h"
#include <iostream>
#include <fstream>
#include <vector>
#include <memory>
#include <random>
#include <chrono>
#include <algorithm>
#include <thread>

// Simple RL Agent interfaces
class RLAgent {
public:
    virtual ~RLAgent() = default;
    virtual std::vector<int> get_action(const std::vector<float>& observation) = 0;
    virtual void update(const std::vector<float>& observation, 
                       const std::vector<int>& action,
                       float reward, 
                       const std::vector<float>& next_observation,
                       bool done) = 0;
    virtual void save_model(const std::string& filepath) = 0;
    virtual void load_model(const std::string& filepath) = 0;
};

// Random baseline agent
class RandomAgent : public RLAgent {
private:
    std::mt19937 rng;
    std::uniform_int_distribution<int> action_type_dist;
    std::uniform_int_distribution<int> position_dist;
    
public:
    RandomAgent() : rng(std::chrono::steady_clock::now().time_since_epoch().count()),
                   action_type_dist(0, 5), position_dist(0, 19) {}
    
    std::vector<int> get_action(const std::vector<float>& observation) override {
        return {action_type_dist(rng), position_dist(rng), position_dist(rng)};
    }
    
    void update(const std::vector<float>& observation, 
               const std::vector<int>& action,
               float reward, 
               const std::vector<float>& next_observation,
               bool done) override {
        // Random agent doesn't learn
    }
    
    void save_model(const std::string& filepath) override {}
    void load_model(const std::string& filepath) override {}
};

int main(int argc, char* argv[]) {
    std::cout << "Mini Motorways RL - OpenGL Version" << std::endl;
    std::cout << "==================================" << std::endl;
    
    if (argc < 2) {
        std::cout << "Usage:" << std::endl;
        std::cout << "  " << argv[0] << " demo" << std::endl;
        std::cout << "  " << argv[0] << " train [episodes]" << std::endl;
        return 1;
    }
    
    std::string mode = argv[1];
    
    if (mode == "demo") {
        std::cout << "Running interactive demo..." << std::endl;
        
        MiniMotorwaysEnvironment env;
        if (!env.initialize()) {
            std::cerr << "Failed to initialize environment" << std::endl;
            return 1;
        }
        
        RandomAgent agent;
        std::vector<float> observation = env.reset();
        
        std::cout << "Demo running... Close window to exit." << std::endl;
        
        while (!env.should_close() && !env.is_done()) {
            std::vector<int> action = agent.get_action(observation);
            observation = env.step(action);
            
            env.render();
            std::this_thread::sleep_for(std::chrono::milliseconds(200));
        }
        
        std::cout << "Demo finished. Final score: " << env.get_score() << " | Construction spent: " << env.get_construction_cost() << " points" << std::endl;
        
    } else if (mode == "train") {
        int episodes = (argc > 2) ? std::stoi(argv[2]) : 100;
        
        std::cout << "Training random agent for " << episodes << " episodes..." << std::endl;
        
        MiniMotorwaysEnvironment env;
        if (!env.initialize()) {
            std::cerr << "Failed to initialize environment" << std::endl;
            return 1;
        }
        
        RandomAgent agent;
        std::vector<int> scores;
        
        for (int episode = 0; episode < episodes; episode++) {
            std::vector<float> observation = env.reset();
            float total_reward = 0.0f;
            
            while (!env.is_done()) {
                std::vector<int> action = agent.get_action(observation);
                observation = env.step(action);
                total_reward += 1.0f; // Simple reward
                
                // Render every 10th episode
                if (episode % 10 == 0) {
                    env.render();
                    std::this_thread::sleep_for(std::chrono::milliseconds(50));
                }
            }
            
            scores.push_back(env.get_score());
            
            if (episode % 10 == 0) {
                std::cout << "Episode " << episode << " - Score: " << env.get_score() << " | Construction spent: " << env.get_construction_cost() << " points" << std::endl;
            }
        }
        
        // Calculate average score
        float avg_score = 0;
        for (int score : scores) {
            avg_score += score;
        }
        avg_score /= scores.size();
        
        std::cout << "Training completed!" << std::endl;
        std::cout << "Average score: " << avg_score << std::endl;
        
    } else {
        std::cerr << "Unknown mode: " << mode << std::endl;
        return 1;
    }
    
    return 0;
}
