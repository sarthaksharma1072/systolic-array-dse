`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 24.10.2026 23:17:06
// Design Name: 
// Module Name: top
// Project Name: 
// Target Devices: 
// Tool Versions: 
// Description: 
// 
// Dependencies: 
// 
// Revision:
// Revision 0.01 - File Created
// Additional Comments:
// 
//////////////////////////////////////////////////////////////////////////////////


module top #(
    parameter N        = 4,
    parameter M        = 4,
    parameter WIDTH    = 8,
    parameter ACCW     = 32,
    parameter DATAFLOW = 1
)(
    input  wire                    clk,
    input  wire                    rst,
    input  wire                    start,
    // load activations
    input  wire                    we_a,
    input  wire [15:0]             addr_a,
    input  wire signed [WIDTH-1:0] data_a,
    // load weights
    input  wire                    we_b,
    input  wire [15:0]             addr_b,
    input  wire signed [WIDTH-1:0] data_b,
    // read results
    input  wire [15:0]             addr_c,
    output wire signed [ACCW-1:0]  data_c,
    output wire                    done
);
    reg signed [WIDTH-1:0] a_mem [0:M*N-1];
    reg signed [ACCW-1:0]  c_mem [0:M*N-1];
    reg        [N*N*WIDTH-1:0] w_flat;

    wire        load_w, en, capture;
    wire [15:0] t;

    ctrl_fsm #(.N(N), .M(M), .DATAFLOW(DATAFLOW)) u_fsm (
        .clk(clk), .rst(rst), .start(start),
        .load_w(load_w), .en(en), .capture(capture), .t(t), .done(done));

    // ---- activation feed, row r delayed by r cycles
    reg [N*WIDTH-1:0] a_edge;
    integer r, ti;
    always @(*) begin
        ti     = t;
        a_edge = {N*WIDTH{1'b0}};
        for (r = 0; r < N; r = r + 1)
            if ((ti - r) >= 0 && (ti - r) < M)
                a_edge[r*WIDTH +: WIDTH] = a_mem[(ti-r)*N + r];
    end

    wire [N*N*ACCW-1:0] acc_flat;
    wire [N*ACCW-1:0]   v_bottom;

    systolic_array #(.N(N), .WIDTH(WIDTH), .ACCW(ACCW), .DATAFLOW(DATAFLOW)) u_sa (
        .clk(clk), .rst(rst), .en(en), .load_w(load_w), .w_flat(w_flat),
        .a_edge(a_edge), .v_edge({N*ACCW{1'b0}}),
        .acc_flat(acc_flat), .v_bottom(v_bottom));

    // ---- loads and result capture
    integer c, idx, tc;
    always @(posedge clk) begin
        if (we_a) a_mem[addr_a] <= data_a;
        if (we_b) w_flat[addr_b*WIDTH +: WIDTH] <= data_b;
        if (capture) begin
            tc = t;
            for (c = 0; c < N; c = c + 1) begin
                idx = tc - N - c;
                if (idx >= 0 && idx < M)
                    c_mem[idx*N + c] <= v_bottom[c*ACCW +: ACCW];
            end
        end
    end

    assign data_c = c_mem[addr_c];
endmodule
