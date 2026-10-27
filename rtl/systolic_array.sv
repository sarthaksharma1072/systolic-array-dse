`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 24.10.2026 21:36:01
// Design Name: 
// Module Name: systolic_array
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


module systolic_array #(
    parameter N        = 4,
    parameter WIDTH    = 8,
    parameter ACCW     = 32,
    parameter DATAFLOW = 0
)(
    input  wire                   clk,
    input  wire                   rst,
    input  wire                   en,
    input  wire                   load_w,
    input  wire [N*N*WIDTH-1:0]   w_flat,
    input  wire [N*WIDTH-1:0]     a_edge,
    input  wire [N*ACCW-1:0]      v_edge,
    output wire [N*N*ACCW-1:0]    acc_flat,
    output wire [N*ACCW-1:0]      v_bottom
);
    wire signed [WIDTH-1:0] a_h [0:N-1][0:N];
    wire signed [ACCW-1:0]  v_v [0:N][0:N-1];

    genvar i, j;
    generate
        for (i = 0; i < N; i = i + 1) begin : g_left
            assign a_h[i][0] = a_edge[i*WIDTH +: WIDTH];
        end
        for (j = 0; j < N; j = j + 1) begin : g_top
            assign v_v[0][j] = v_edge[j*ACCW +: ACCW];
        end
        for (i = 0; i < N; i = i + 1) begin : g_row
            for (j = 0; j < N; j = j + 1) begin : g_col
                pe #(.WIDTH(WIDTH), .ACCW(ACCW), .DATAFLOW(DATAFLOW)) u_pe (
                    .clk(clk), .rst(rst), .en(en), .load_w(load_w),
                    .w_in  (w_flat[(i*N+j)*WIDTH +: WIDTH]),
                    .a_in  (a_h[i][j]),
                    .a_out (a_h[i][j+1]),
                    .v_in  (v_v[i][j]),
                    .v_out (v_v[i+1][j]),
                    .acc   (acc_flat[(i*N+j)*ACCW +: ACCW])
                );
            end
        end
        for (j = 0; j < N; j = j + 1) begin : g_bot
            assign v_bottom[j*ACCW +: ACCW] = v_v[N][j];
        end
    endgenerate
endmodule
