`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 24.10.2026 23:25:23
// Design Name: 
// Module Name: tb_top
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

`timescale 1ns/1ps
module tb_top;
    localparam N = 4, M = 4, WIDTH = 8, ACCW = 32;

    reg clk = 0, rst = 1, start = 0;
    always #5 clk = ~clk;

    reg                    we_a = 0, we_b = 0;
    reg [15:0]             addr_a = 0, addr_b = 0, addr_c = 0;
    reg signed [WIDTH-1:0] data_a = 0, data_b = 0;
    wire signed [ACCW-1:0] data_c;
    wire                   done;

    top #(.N(N), .M(M), .WIDTH(WIDTH), .ACCW(ACCW), .DATAFLOW(1)) dut (
        .clk(clk), .rst(rst), .start(start),
        .we_a(we_a), .addr_a(addr_a), .data_a(data_a),
        .we_b(we_b), .addr_b(addr_b), .data_b(data_b),
        .addr_c(addr_c), .data_c(data_c), .done(done));

    reg signed [WIDTH-1:0] A [0:M*N-1];
    reg signed [WIDTH-1:0] B [0:N*N-1];
    reg signed [ACCW-1:0]  C [0:M*N-1];

    integer i, errors;

    initial begin
        #20000;
        $display("TIMEOUT - done never asserted");
        $finish;
    end

    initial begin
        $readmemh("C:/Users/ROG/systolic_array/stim/A.hex", A);
        $readmemh("C:/Users/ROG/systolic_array/stim/B.hex", B);
        $readmemh("C:/Users/ROG/systolic_array/stim/C.hex", C);

        repeat (3) @(negedge clk);
        rst = 0;

        for (i = 0; i < M*N; i = i + 1) begin
            we_a = 1; addr_a = i[15:0]; data_a = A[i];
            @(negedge clk);
        end
        we_a = 0;

        for (i = 0; i < N*N; i = i + 1) begin
            we_b = 1; addr_b = i[15:0]; data_b = B[i];
            @(negedge clk);
        end
        we_b = 0;

        @(negedge clk);
        start = 1; @(negedge clk); start = 0;

        wait (done === 1'b1);
        @(negedge clk);

        errors = 0;
        for (i = 0; i < M*N; i = i + 1) begin
            addr_c = i[15:0];
            #1;
            if (data_c !== C[i]) begin
                $display("FAIL C[%0d] expected %0d got %0d", i, C[i], data_c);
                errors = errors + 1;
            end
        end

        if (errors == 0) $display("PASS TOP: all %0d outputs match", M*N);
        else             $display("FAIL TOP: %0d mismatches", errors);
        $finish;
    end
endmodule