`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 24.10.2026 21:31:34
// Design Name: 
// Module Name: pe
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


module pe #(
    parameter WIDTH    = 8,
    parameter ACCW     = 32,
    parameter DATAFLOW = 0          // 0 = output stationary, 1 = weight stationary
)(
    input  wire                    clk,
    input  wire                    rst,
    input  wire                    en,
    input  wire                    load_w,
    input  wire signed [WIDTH-1:0] w_in,
    input  wire signed [WIDTH-1:0] a_in,
    output wire signed [WIDTH-1:0] a_out,
    input  wire signed [ACCW-1:0]  v_in,
    output wire signed [ACCW-1:0]  v_out,
    output wire signed [ACCW-1:0]  acc
);
    reg signed [WIDTH-1:0] a_r;
    reg signed [ACCW-1:0]  v_r;
    assign a_out = a_r;
    assign v_out = v_r;

    generate
    if (DATAFLOW == 0) begin : g_os
        reg signed [ACCW-1:0] acc_r;
        always @(posedge clk) begin
            if (rst) begin
                a_r <= {WIDTH{1'b0}}; v_r <= {ACCW{1'b0}}; acc_r <= {ACCW{1'b0}};
            end else if (en) begin
                a_r   <= a_in;
                v_r   <= v_in;
                acc_r <= acc_r + a_in * $signed(v_in[WIDTH-1:0]);
            end
        end
        assign acc = acc_r;
    end else begin : g_ws
        reg signed [WIDTH-1:0] w_r;
        always @(posedge clk) begin
            if (rst) begin
                a_r <= {WIDTH{1'b0}}; v_r <= {ACCW{1'b0}}; w_r <= {WIDTH{1'b0}};
            end else if (load_w) begin
                w_r <= w_in;
            end else if (en) begin
                a_r <= a_in;
                v_r <= v_in + a_in * w_r;
            end
        end
        assign acc = {ACCW{1'b0}};
    end
    endgenerate
endmodule
