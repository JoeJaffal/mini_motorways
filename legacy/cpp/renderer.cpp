#include "mini_motorways_env.h"
#include <iostream>
#include <sstream>

// Vertex shader source
const std::string vertex_shader_source = R"(
#version 330 core
layout (location = 0) in vec2 aPos;

uniform mat4 projection;
uniform mat4 model;
uniform vec3 color;

out vec3 vertexColor;
 out vec2 localPos;

void main()
{
    gl_Position = projection * model * vec4(aPos, 0.0, 1.0);
    vertexColor = color;
    localPos = aPos;
}
)";

// Fragment shader source
const std::string fragment_shader_source = R"(
#version 330 core
in vec3 vertexColor;
 in vec2 localPos;
 uniform vec2 boxSize;
 uniform float cornerRadius;
 out vec4 FragColor;

void main()
{
    float alpha = 1.0;
    if (cornerRadius > 0.0) {
        vec2 q = abs((localPos - 0.5) * boxSize) - boxSize * 0.5 + cornerRadius;
        float distance = length(max(q, 0.0)) + min(max(q.x, q.y), 0.0) - cornerRadius;
        alpha = 1.0 - smoothstep(-fwidth(distance), fwidth(distance), distance);
    }
    FragColor = vec4(vertexColor, alpha);
}
)";

Renderer::Renderer() : shader_program(0), vao(0), vbo(0) {
    // Initialize color mappings
    tile_colors[TileType::EMPTY] = glm::vec3(0.1f, 0.1f, 0.1f);       // Dark gray
    tile_colors[TileType::HOUSE] = glm::vec3(0.8f, 0.2f, 0.2f);       // Red
    tile_colors[TileType::BUSINESS] = glm::vec3(0.2f, 0.2f, 0.8f);    // Blue
    tile_colors[TileType::ROAD] = glm::vec3(0.5f, 0.5f, 0.5f);        // Gray
    tile_colors[TileType::BRIDGE] = glm::vec3(0.6f, 0.4f, 0.2f);      // Brown
    tile_colors[TileType::ROUNDABOUT] = glm::vec3(0.8f, 0.6f, 0.2f);  // Orange
    tile_colors[TileType::TRAFFIC_LIGHT] = glm::vec3(0.8f, 0.8f, 0.2f); // Yellow

    car_colors[CarColor::RED] = glm::vec3(0.91f, 0.32f, 0.39f);
    car_colors[CarColor::BLUE] = glm::vec3(0.40f, 0.69f, 0.82f);
    car_colors[CarColor::GREEN] = glm::vec3(0.41f, 0.72f, 0.60f);
    car_colors[CarColor::YELLOW] = glm::vec3(1.0f, 1.0f, 0.0f);
    car_colors[CarColor::PURPLE] = glm::vec3(1.0f, 0.0f, 1.0f);
    car_colors[CarColor::ORANGE] = glm::vec3(1.0f, 0.5f, 0.0f);
}

Renderer::~Renderer() {
    if (vao) glDeleteVertexArrays(1, &vao);
    if (vbo) glDeleteBuffers(1, &vbo);
    if (shader_program) glDeleteProgram(shader_program);
}

bool Renderer::initialize() {
    // Create and compile shaders
    shader_program = load_shader(vertex_shader_source, fragment_shader_source);
    if (shader_program == 0) {
        std::cerr << "Failed to create shader program" << std::endl;
        return false;
    }

    // Setup quad for rendering
    setup_quad();

    // Setup projection matrix (orthographic for 2D)
    projection = glm::ortho(0.0f, 30.0f, 20.0f, 0.0f, -1.0f, 1.0f);

    return true;
}

void Renderer::render_frame(const MiniMotorwaysEnvironment& env) {
    glUseProgram(shader_program);

    // Set projection matrix
    GLint proj_loc = glGetUniformLocation(shader_program, "projection");
    glUniformMatrix4fv(proj_loc, 1, GL_FALSE, glm::value_ptr(projection));

    // Render grid background
    render_grid(env.get_grid());

    // Render buildings
    render_buildings(env.get_buildings());

    // Render cars
    render_cars(env.get_cars());

    // Render UI
    render_ui(env.get_score(), env.get_step(), env.get_construction_cost());
}

namespace {
const glm::vec3 ink(0.32f, 0.37f, 0.36f), asphalt(1.0f, 0.995f, 0.96f);
const glm::vec3 paper(0.99f, 0.98f, 0.92f), grass(0.98f, 0.95f, 0.83f);
void rect(GLuint program, float x, float y, float w, float h, glm::vec3 color, float radius = 0.0f) {
    glm::mat4 model(1.0f);
    model = glm::translate(model, glm::vec3(x, y, 0));
    model = glm::scale(model, glm::vec3(w, h, 1));
    glUniformMatrix4fv(glGetUniformLocation(program, "model"), 1, GL_FALSE, glm::value_ptr(model));
    glUniform3fv(glGetUniformLocation(program, "color"), 1, glm::value_ptr(color));
    glUniform2f(glGetUniformLocation(program, "boxSize"), w, h);
    glUniform1f(glGetUniformLocation(program, "cornerRadius"), radius);
    glDrawArrays(GL_TRIANGLES, 0, 6);
}
void disc(GLuint program, float x, float y, float radius, glm::vec3 color) {
    rect(program, x-radius, y-radius, radius*2, radius*2, color, radius);
}
const std::unordered_map<char, std::string> font = {
 {'A',"01110100011000111111100011000110001"}, {'B',"11110100011000111110100011000111110"},
 {'C',"01111100001000010000100001000001111"}, {'D',"11110100011000110001100011000111110"},
 {'E',"11111100001000011110100001000011111"}, {'F',"11111100001000011110100001000010000"},
 {'G',"01111100001000010111100011000101111"}, {'H',"10001100011000111111100011000110001"},
 {'I',"11111001000010000100001000010011111"}, {'J',"00111000100001000010100101001001100"},
 {'K',"10001100101010011000101001001010001"}, {'L',"10000100001000010000100001000011111"},
 {'M',"10001110111010110101100011000110001"}, {'N',"10001110011010110011100011000110001"},
 {'O',"01110100011000110001100011000101110"}, {'P',"11110100011000111110100001000010000"},
 {'Q',"01110100011000110001101011001001101"}, {'R',"11110100011000111110101001001010001"},
 {'S',"01111100001000001110000010000111110"}, {'T',"11111001000010000100001000010000100"},
 {'U',"10001100011000110001100011000101110"}, {'V',"10001100011000110001100010101000100"},
 {'W',"10001100011000110101101011101110001"}, {'X',"10001100010101000100010101000110001"},
 {'Y',"10001100010101000100001000010000100"}, {'Z',"11111000010001000100010001000011111"},
 {'0',"01110100011001110101110011000101110"}, {'1',"00100011000010000100001000010001110"},
 {'2',"01110100010000100010001000100011111"}, {'3',"11110000010000101110000010000111110"},
 {'4',"00010001100101010010111110001000010"}, {'5',"11111100001000011110000010000111110"},
 {'6',"01110100001000011110100011000101110"}, {'7',"11111000010001000100010000100001000"},
 {'8',"01110100011000101110100011000101110"}, {'9',"01110100011000101111000010000101110"},
 {':',"00000001000010000000001000010000000"}, {'-',"00000000000000011111000000000000000"}
};
void text(GLuint program, float x, float y, const std::string& value, float size = 0.04f, glm::vec3 color = ink) {
    for (char c : value) {
        auto found = font.find(c);
        if (found != font.end())
            for (int row = 0; row < 7; ++row)
                for (int col = 0; col < 5; ++col)
                    if (found->second[row * 5 + col] == '1')
                        rect(program, x + col * size, y + row * size, size, size, color);
        x += size * 6;
    }
}
void road(GLuint p, float x, float y, TileType tile, bool up, bool right, bool down, bool left) {
    // A warm outline, slight offset shadow, and pale continuous road surface.
    auto stroke = [&](float width, glm::vec3 color, float offset) {
        float a=.5f-width/2;
        disc(p,x+.5f+offset,y+.5f+offset,width/2,color);
        if(up) rect(p,x+a+offset,y+offset,width,.5f,color);
        if(right) rect(p,x+.5f+offset,y+a+offset,.5f,width,color);
        if(down) rect(p,x+a+offset,y+.5f+offset,width,.5f,color);
        if(left) rect(p,x+offset,y+a+offset,.5f,width,color);
    };
    stroke(.52f,glm::vec3(.87f,.84f,.72f),.045f);
    stroke(.49f,glm::vec3(.87f,.85f,.76f),0);
    stroke(.38f,asphalt,0);
    if (tile == TileType::BRIDGE) {
        const glm::vec3 rail(.76f,.72f,.60f);
        bool horizontal=(left||right)&&!(up||down);
        if(horizontal) {
            rect(p,x,y+.24f,1,.045f,rail,.02f);
            rect(p,x,y+.72f,1,.045f,rail,.02f);
        } else {
            rect(p,x+.24f,y,.045f,1,rail,.02f);
            rect(p,x+.72f,y,.045f,1,rail,.02f);
        }
    } else if(tile==TileType::ROUNDABOUT) {
        disc(p,x+.5f,y+.5f,.43f,glm::vec3(.87f,.85f,.76f));
        disc(p,x+.5f,y+.5f,.38f,asphalt);
        disc(p,x+.5f,y+.5f,.22f,glm::vec3(.90f,.90f,.57f));
        disc(p,x+.47f,y+.47f,.085f,glm::vec3(.67f,.76f,.35f));
    } else if(tile==TileType::TRAFFIC_LIGHT) {
        rect(p,x+.64f,y+.15f,.13f,.34f,ink,.035f);
        disc(p,x+.705f,y+.23f,.035f,glm::vec3(.94f,.36f,.35f));
        disc(p,x+.705f,y+.40f,.035f,glm::vec3(.53f,.73f,.45f));
    }
}
void building(GLuint p, float x, float y, bool house, glm::vec3 color) {
    const glm::vec3 shadow(.86f,.83f,.71f);
    // Top-down parcels, offset cast shadows, and colored beveled roofs.
    float w=house?.43f:.78f, h=house?.43f:.82f;
    float bx=x+.5f-w/2, by=y+.5f-h/2;
    for(int i=12;i>=1;--i)
        rect(p,bx+i*.025f,by+i*.025f,w,h,shadow,.075f);
    rect(p,bx-.06f,by-.06f,w+.12f,h+.12f,asphalt,.09f);
    if(house) {
        rect(p,bx,by,w,h,color*.76f,.045f);
        rect(p,bx+.025f,by+.025f,w-.07f,h-.085f,color,.025f);
        rect(p,bx+.045f,by+.04f,w-.12f,.035f,glm::mix(color,asphalt,.40f),.012f);
        rect(p,bx+.09f,by+h-.04f,.12f,.07f,color*.65f,.012f);
    } else {
        rect(p,bx+.08f,by+.08f,w-.16f,.47f,color*.72f,.065f);
        rect(p,bx+.1f,by+.08f,w-.22f,.40f,color,.045f);
        rect(p,bx+.13f,by+.10f,w-.29f,.04f,glm::mix(color,asphalt,.50f),.012f);
        // Parking bays distinguish destinations from houses even at small scale.
        for(int i=0;i<3;++i) {
            rect(p,bx+.10f+i*.20f,by+.63f,.13f,.12f,glm::vec3(.89f,.88f,.80f),.01f);
            rect(p,bx+.13f+i*.20f,by+.64f,.07f,.10f,asphalt,.008f);
        }
    }
}
}
void Renderer::render_grid(const std::vector<std::vector<TileType>>& grid) {
    glBindVertexArray(vao);
    rect(shader_program,0,0,20,20,grass);
    // Quiet park details only occupy empty cells; they never hide a playable tile.
    for(int y=0;y<static_cast<int>(grid.size());++y)
        for(int x=0;x<static_cast<int>(grid[y].size());++x) {
            if(grid[y][x]!=TileType::EMPTY || (x*17+y*31)%29!=0) continue;
            rect(shader_program,x+.08f,y+.10f,.84f,.78f,glm::vec3(.92f,.92f,.64f),.25f);
            for(int i=0;i<3;++i) {
                float tx=x+.33f+(i%2)*.22f,ty=y+.30f+(i/2)*.24f;
                disc(shader_program,tx+.035f,ty+.045f,.09f,glm::vec3(.80f,.82f,.47f));
                disc(shader_program,tx,ty,.085f,glm::vec3(.69f,.76f,.36f));
                disc(shader_program,tx-.025f,ty-.03f,.045f,glm::vec3(.77f,.82f,.43f));
            }
        }    auto passable = [&](int x,int y) {
        return y>=0 && y<static_cast<int>(grid.size()) && x>=0 &&
            x<static_cast<int>(grid[y].size()) && grid[y][x]!=TileType::EMPTY;
    };
    for(int y=0;y<static_cast<int>(grid.size());++y)
        for(int x=0;x<static_cast<int>(grid[y].size());++x) {
            TileType t=grid[y][x];
            if(t==TileType::ROAD || t==TileType::BRIDGE || t==TileType::ROUNDABOUT || t==TileType::TRAFFIC_LIGHT)
                road(shader_program,float(x),float(y),t,passable(x,y-1),passable(x+1,y),passable(x,y+1),passable(x-1,y));
        }
}
void Renderer::render_buildings(const std::vector<Building>& buildings) {
    glBindVertexArray(vao);
    for(const auto& b:buildings)
        building(shader_program,float(b.position.x),float(b.position.y),b.type==TileType::HOUSE,car_colors[b.color]);
}
void Renderer::render_cars(const std::vector<std::shared_ptr<Car>>& cars) {
    glBindVertexArray(vao);
    for(const auto& car:cars) {
        if(car->completed) continue;
        float x=car->visual_x+.37f,y=car->visual_y+.40f;
        rect(shader_program,x+.045f,y+.065f,.26f,.19f,glm::vec3(.80f,.78f,.67f),.035f);
        rect(shader_program,x,y,.26f,.19f,car_colors[car->color]*.75f,.035f);
        rect(shader_program,x+.01f,y+.01f,.23f,.13f,car_colors[car->color],.025f);
        rect(shader_program,x+.13f,y+.025f,.055f,.10f,glm::mix(car_colors[car->color],asphalt,.55f),.012f);
    }
}
void Renderer::render_ui(int score, int step, int construction_cost) {
    glBindVertexArray(vao);
    rect(shader_program,20,0,10,20,paper);
    rect(shader_program,20,0,.025f,20,glm::vec3(.87f,.85f,.76f));
    text(shader_program,20.65f,.7f,"MINI MOTORWAYS",.067f);
    text(shader_program,20.65f,1.55f,"RANDOM AGENT DEMO",.04f);
    text(shader_program,20.65f,2.45f,"TRIPS COMPLETED",.04f);
    text(shader_program,20.65f,3.0f,std::to_string(score),.1f);
    text(shader_program,24.8f,2.45f,"TOTAL SPENT",.04f);
    text(shader_program,24.8f,3.0f,std::to_string(construction_cost),.1f);
    text(shader_program,20.65f,4.1f,"STEP " + std::to_string(step) + " OF 1000",.04f);
    rect(shader_program,20.65f,4.8f,8.6f,.035f,glm::vec3(.72f,.78f,.71f));
    text(shader_program,20.65f,5.3f,"MAP LEGEND",.05f);
    building(shader_program,20.6f,6.05f,true,car_colors[CarColor::RED]);
    text(shader_program,22,6.35f,"HOUSE - CARS START HERE");
    building(shader_program,20.6f,7.3f,false,car_colors[CarColor::RED]);
    text(shader_program,22,7.6f,"SHOP - MATCH HOUSE COLOR");
    road(shader_program,20.6f,8.55f,TileType::ROAD,false,true,false,true);
    text(shader_program,22,8.9f,"ROAD             1 POINT");
    road(shader_program,20.6f,9.8f,TileType::TRAFFIC_LIGHT,false,true,false,true);
    text(shader_program,22,10.15f,"TRAFFIC LIGHT    5 POINTS");
    road(shader_program,20.6f,11.05f,TileType::BRIDGE,true,false,true,false);
    text(shader_program,22,11.4f,"BRIDGE          10 POINTS");
    road(shader_program,20.6f,12.3f,TileType::ROUNDABOUT,false,true,false,true);
    text(shader_program,22,12.65f,"ROUNDABOUT       8 POINTS");
    rect(shader_program,20.65f,13.7f,8.6f,.035f,glm::vec3(.72f,.78f,.71f));
    text(shader_program,20.65f,14.3f,"WHAT IS HAPPENING?",.045f);
    text(shader_program,20.65f,15.1f,"THE AGENT BUILDS AT RANDOM.");
    text(shader_program,20.65f,15.7f,"ISOLATED ROADS ARE NORMAL.");
    text(shader_program,20.65f,16.3f,"CARS NEED A CONNECTED ROUTE.");
    text(shader_program,20.65f,17.2f,"UNLIMITED CONSTRUCTION");
    text(shader_program,20.65f,17.8f,"SPENDING TRACKS VALID BUILDS.");
    text(shader_program,20.65f,18.4f,"LIGHTS GO ON EXISTING ROADS.");
}
GLuint Renderer::load_shader(const std::string& vertex_src, const std::string& fragment_src) {
    // Compile vertex shader
    GLuint vertex_shader = glCreateShader(GL_VERTEX_SHADER);
    const char* v_src = vertex_src.c_str();
    glShaderSource(vertex_shader, 1, &v_src, nullptr);
    glCompileShader(vertex_shader);

    // Check vertex shader compilation
    GLint success;
    glGetShaderiv(vertex_shader, GL_COMPILE_STATUS, &success);
    if (!success) {
        char info_log[512];
        glGetShaderInfoLog(vertex_shader, 512, nullptr, info_log);
        std::cerr << "Vertex shader compilation failed: " << info_log << std::endl;
        return 0;
    }

    // Compile fragment shader
    GLuint fragment_shader = glCreateShader(GL_FRAGMENT_SHADER);
    const char* f_src = fragment_src.c_str();
    glShaderSource(fragment_shader, 1, &f_src, nullptr);
    glCompileShader(fragment_shader);

    // Check fragment shader compilation
    glGetShaderiv(fragment_shader, GL_COMPILE_STATUS, &success);
    if (!success) {
        char info_log[512];
        glGetShaderInfoLog(fragment_shader, 512, nullptr, info_log);
        std::cerr << "Fragment shader compilation failed: " << info_log << std::endl;
        return 0;
    }

    // Link shaders
    GLuint program = glCreateProgram();
    glAttachShader(program, vertex_shader);
    glAttachShader(program, fragment_shader);
    glLinkProgram(program);

    // Check linking
    glGetProgramiv(program, GL_LINK_STATUS, &success);
    if (!success) {
        char info_log[512];
        glGetProgramInfoLog(program, 512, nullptr, info_log);
        std::cerr << "Shader program linking failed: " << info_log << std::endl;
        return 0;
    }

    // Clean up shaders
    glDeleteShader(vertex_shader);
    glDeleteShader(fragment_shader);

    return program;
}

void Renderer::setup_quad() {
    // Quad vertices (2 triangles)
    float vertices[] = {
        // Triangle 1
        0.0f, 0.0f,  // Bottom-left
        1.0f, 0.0f,  // Bottom-right
        0.0f, 1.0f,  // Top-left

        // Triangle 2
        1.0f, 0.0f,  // Bottom-right
        1.0f, 1.0f,  // Top-right
        0.0f, 1.0f   // Top-left
    };

    glGenVertexArrays(1, &vao);
    glGenBuffers(1, &vbo);

    glBindVertexArray(vao);
    glBindBuffer(GL_ARRAY_BUFFER, vbo);
    glBufferData(GL_ARRAY_BUFFER, sizeof(vertices), vertices, GL_STATIC_DRAW);

    // Position attribute
    glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 2 * sizeof(float), (void*)0);
    glEnableVertexAttribArray(0);

    glBindBuffer(GL_ARRAY_BUFFER, 0);
    glBindVertexArray(0);
}
