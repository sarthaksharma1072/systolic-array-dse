`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 24.10.2026 22:23:33
// Design Name: 
// Module Name: tb_os
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
module tb_os;
    localparam N = 4, K = 4, WIDTH = 8, ACCW = 32;

    reg clk = 0, rst = 1, en = 0;
    always #5 clk = ~clk;

    reg signed [WIDTH-1:0] A [0:N*K-1];
    reg signed [WIDTH-1:0] B [0:K*N-1];
    reg signed [ACCW-1:0]  C [0:N*N-1];

    reg  [N*WIDTH-1:0]   a_edge;
    reg  [N*ACCW-1:0]    v_edge;
    wire [N*N*ACCW-1:0]  acc_flat;
    wire [N*ACCW-1:0]    v_bottom;

    systolic_array #(.N(N), .WIDTH(WIDTH), .ACCW(ACCW), .DATAFLOW(0)) dut (
        .clk(clk), .rst(rst), .en(en), .load_w(1'b0), .w_flat({N*N*WIDTH{1'b0}}),
        .a_edge(a_edge), .v_edge(v_edge),
        .acc_flat(acc_flat), .v_bottom(v_bottom));

    integer t, i, j, errors, cycles;
    reg signed [ACCW-1:0]  got;
    reg signed [WIDTH-1:0] aw, bw;

    initial begin
        $readmemh("C:/Users/ROG/systolic_array/stim/A.hex", A);
        $readmemh("C:/Users/ROG/systolic_array/stim/B.hex", B);
        $readmemh("C:/Users/ROG/systolic_array/stim/C.hex", C);

        a_edge = 0; v_edge = 0;
        repeat (2) @(negedge clk);
        rst = 0; en = 1; cycles = 0;

        for (t = 0; t < K + 2*N + 2; t = t + 1) begin
            for (i = 0; i < N; i = i + 1) begin
                aw = ((t-i) >= 0 && (t-i) < K) ? A[i*K + (t-i)] : {WIDTH{1'b0}};
                a_edge[i*WIDTH +: WIDTH] = aw;
            end
            for (j = 0; j < N; j = j + 1) begin
                bw = ((t-j) >= 0 && (t-j) < K) ? B[(t-j)*N + j] : {WIDTH{1'b0}};
                v_edge[j*ACCW +: ACCW] = {{(ACCW-WIDTH){bw[WIDTH-1]}}, bw};
            end
            @(negedge clk);
            cycles = cycles + 1;
        end

        errors = 0;
        for (i = 0; i < N; i = i + 1)
            for (j = 0; j < N; j = j + 1) begin
                got = acc_flat[(i*N+j)*ACCW +: ACCW];
                if (got !== C[i*N+j]) begin
                    $display("FAIL C[%0d][%0d] expected %0d got %0d", i, j, C[i*N+j], got);
                    errors = errors + 1;
                end
            end

        if (errors == 0) $display("PASS OS: all %0d outputs match, %0d cycles", N*N, cycles);
        else             $display("FAIL OS: %0d mismatches", errors);
        $finish;
    end
endmodule
