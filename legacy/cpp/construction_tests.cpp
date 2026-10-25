#include "mini_motorways_env.h"
#include <stdexcept>

void require(bool condition) {
    if (!condition) throw std::runtime_error("Construction economy check failed");
}
int main(int argc, char* argv[]) {
    MiniMotorwaysEnvironment env;
    env.reset();
    require(env.get_construction_cost() == 0);
    require(env.get_observation().size() == 805);
    for (int action = 0; action < 3; ++action) {
        auto pos = env.find_empty_position();
        require(env.execute_action(action, pos.x, pos.y));
    }
    require(env.get_construction_cost() == 19);
    auto pos = env.find_empty_position();
    require(!env.execute_action(3, pos.x, pos.y));
    require(env.get_construction_cost() == 19);
    require(env.execute_action(0, pos.x, pos.y));
    require(env.execute_action(3, pos.x, pos.y));
    require(env.get_construction_cost() == 25);
    require(!env.execute_action(3, pos.x, pos.y));
    require(!env.execute_action(0, -1, 0));
    require(!env.execute_action(6, pos.x, pos.y));
    require(env.get_construction_cost() == 25);
    require(env.execute_action(4, pos.x, pos.y));
    require(env.get_construction_cost() == 25);
    // Repeated purchases remain possible beyond the old inventory limits.
    for (int i = 0; i < 100; ++i) {
        require(env.execute_action(1, pos.x, pos.y));
        require(env.execute_action(4, pos.x, pos.y));
    }
    require(env.get_construction_cost() == 1025);
    require(env.get_score() == 0);
    auto observation = env.step({5, 0, 0});
    require(env.get_step() == 1 && env.get_construction_cost() == 1025);
    env.reset();
    require(env.get_construction_cost() == 0 && env.get_score() == 0);
    if (argc > 1 && std::string(argv[1]) == "--preview") {
        require(env.initialize());
        env.reset();
        for (int x = 2; x < 17; ++x) env.execute_action(0, x, 10);
        env.execute_action(3, 5, 10);
        env.execute_action(2, 10, 11);
        env.execute_action(1, 13, 11);
        Renderer preview;
        require(preview.initialize());
        preview.render_frame(env);
        glFinish();
        const int width = 1200, height = 800;
        std::vector<unsigned char> pixels(width * height * 3);
        glReadBuffer(GL_BACK);
        glReadPixels(0, 0, width, height, GL_BGR, GL_UNSIGNED_BYTE, pixels.data());
        require(glGetError() == GL_NO_ERROR);
        unsigned char header[54] = {};
        header[0] = 'B'; header[1] = 'M'; header[10] = 54; header[14] = 40;
        auto field = [&](int offset, unsigned int value) {
            for (int i = 0; i < 4; ++i) header[offset+i] = (value >> (8*i)) & 255;
        };
        field(2, 54 + static_cast<unsigned int>(pixels.size()));
        field(18, width); field(22, height); header[26] = 1; header[28] = 24;
        std::ofstream output("preview.bmp", std::ios::binary);
        output.write(reinterpret_cast<char*>(header), sizeof(header));
        output.write(reinterpret_cast<char*>(pixels.data()), pixels.size());
        require(output.good());
        std::cout << "OpenGL preview rendered successfully\n";
    }
    std::cout << "Construction economy checks passed\n";
}
