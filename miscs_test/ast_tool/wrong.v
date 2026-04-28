module simple_counter(clk, rst, count);
  input clk, rst;
  output reg count; // Error 1: 'count' should be declared as a vector for a counter
  always @(posedge clk or rst) // Error 2: Missing 'posedge' or 'negedge' for 'rst'
  begin
    if (rst)
      count <= 0;
    else
      count = count + 1; // Error 3: Should use non-blocking assignment '<=' in sequential logic
  end
endmodule
