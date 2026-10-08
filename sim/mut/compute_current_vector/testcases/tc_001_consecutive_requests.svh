task automatic drive_request(input int request_index);
        @(negedge clk);
        while (!ready) begin
            busy_observed = 1'b1;
            @(negedge clk);
        end
        current_in = stimulus_current[request_index];
        id_in = 2'(request_index % NUM_NEURONS);
        for (int state_index = 0; state_index < 4; state_index++) begin
            neuron_state_variables[state_index] = stimulus_states[request_index][state_index];
        end
        valid_in = 1'b1;
        @(negedge clk);
        valid_in = 1'b0;
        current_in = 32'sh12345678;
        neuron_state_variables = '{default: 32'sh76543210};
endtask

task automatic wait_for_results(input int expected_count);
        int timeout_cycles;

        timeout_cycles = 0;
        while (returned_count < expected_count && timeout_cycles < TEST_REQUEST_COUNT * 100) begin
            @(negedge clk);
            timeout_cycles++;
        end
        if (returned_count != expected_count || accepted_count != expected_count) begin
            $fatal(1, "Request count mismatch: accepted=%0d returned=%0d expected=%0d", accepted_count, returned_count, expected_count);
        end
endtask

task automatic run_tc_001_consecutive_requests;
        int timeout_cycles;

        for (int request_index = 0; request_index < TEST_REQUEST_COUNT; request_index++) begin
            stimulus_current[request_index] = (request_index - 48) * 257;
            for (int state_index = 0; state_index < 4; state_index++) begin
                stimulus_states[request_index][state_index] = INITIAL_STATE[state_index] + ((request_index * 11 + state_index * 7) % 31 - 15) * 1048576;
            end
        end
        for (int state_index = 0; state_index < 4; state_index++) begin
            stimulus_states[0][state_index] = '0;
            stimulus_states[1][state_index] = -32'sd134217728;
            stimulus_states[2][state_index] = 32'sd100663296;
        end

        repeat (3) begin
            @(negedge clk);
        end
        rst = 1'b0;

        for (int request_index = 0; request_index < TEST_REQUEST_COUNT; request_index++) begin
            @(negedge clk);
            reference_current = stimulus_current[request_index];
            for (int state_index = 0; state_index < 4; state_index++) begin
                reference_states[state_index] = stimulus_states[request_index][state_index];
            end
            reference_valid_in = 1'b1;
            @(negedge clk);
            reference_valid_in = 1'b0;
            timeout_cycles = 0;
            while (!reference_valid_out && timeout_cycles < 100) begin
                @(negedge clk);
                timeout_cycles++;
            end
            if (!reference_valid_out) begin
                $fatal(1, "Reference timed out for request %0d", request_index);
            end
            for (int vector_index = 0; vector_index < 8; vector_index++) begin
                expected_vectors[request_index][vector_index] = reference_vector[vector_index];
            end
        end

        checking_results = 1'b1;
        for (int request_index = 0; request_index < TEST_REQUEST_COUNT; request_index++) begin
            drive_request(request_index);
        end
        @(negedge clk);
        valid_in = 1'b0;
        current_in = 32'sh12345678;
        neuron_state_variables = '{default: 32'sh76543210};
        wait_for_results(TEST_REQUEST_COUNT);
        if (!busy_observed) begin
            $fatal(1, "Shared engine busy interval was not exercised");
        end

        checking_results = 1'b0;
        drive_request(0);
        @(negedge clk);
        valid_in = 1'b0;
        rst = 1'b1;
        repeat (3) begin
            @(negedge clk);
        end
        rst = 1'b0;
        repeat (50) begin
            @(negedge clk);
            if (valid_out) begin
                $fatal(1, "A pre-reset request produced a result after reset");
            end
        end
        checking_results = 1'b1;
        drive_request(0);
        drive_request(1);
        drive_request(2);
        @(negedge clk);
        valid_in = 1'b0;
        wait_for_results(3);
        $display("Verified %0d vectors and IDs against the scalar reference, ready pacing, input capture and reset recovery", TEST_REQUEST_COUNT + 3);
endtask
