`timescale 1ns/1ps

// Example DUT: ten independent 2:1 mux lanes with per-lane select.
// Replace this example with your actual RTL if its interface is different.
module mux10 (
    input  logic [9:0] a,
    input  logic [9:0] b,
    input  logic [9:0] sel,
    output logic [9:0] y
);
    assign y = (a & ~sel) | (b & sel);
endmodule
