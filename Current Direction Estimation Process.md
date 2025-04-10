# Current Direction Estimation Process

## Theory and Implementation

The Field Scanner application uses a loop magnetic probe to measure the magnetic field at three orientations: 0°, 45°, and 90°. These measurements enable the estimation of current directions on the PCB based on electromagnetic principles.

### Theoretical Background

1. **Relationship Between Magnetic Field and Current**:
   - According to Maxwell's equations, a magnetic field (B) is generated around a current-carrying conductor.
   - The relationship is governed by Ampère's law: ∇ × B = μ₀J + μ₀ε₀(∂E/∂t)
   - For quasi-static fields on PCBs, we can approximate this as: ∇ × B = μ₀J
   - The magnetic field forms concentric circles around a straight wire, with the field direction determined by the right-hand rule.

2. **Loop Probe Measurements**:
   - Our loop probe detects the component of the magnetic field perpendicular to its plane.
   - By rotating the probe to different orientations (0°, 45°, 90°), we measure different projections of the magnetic field vector.
   - These projections provide information about the field's direction and magnitude.

3. **Why Three Angles Are Needed**:
   - Measurements at 0° and 90° provide orthogonal components of the field vector.
   - The 45° measurement helps resolve directional ambiguity and improves the accuracy of angle estimation.
   - Together, these measurements enable the reconstruction of the 2D magnetic field vector.

### Implementation Process

1. **Data Acquisition**:
   - Scan the PCB at three probe orientations: 0°, 45°, and 90°.
   - Record field strength in dBm at each grid point.

2. **Preprocessing**:
   - Convert measurements from dBm (logarithmic) to linear power units using the formula: P_linear = 10^(P_dBm/10)
   - This conversion is necessary because vector arithmetic requires linear quantities.

3. **Field Orientation Calculation**:
   - At each grid point, compute the field orientation using the formula: θ = arctan2(B₉₀ - B₀, B₄₅)
   - Where B₀, B₄₅, and B₉₀ are the field strengths at 0°, 45°, and 90° orientations in linear units.
   - This formula approximates the angle of the magnetic field vector in the 2D plane.

4. **Field Intensity Calculation**:
   - Compute the field intensity using: |B| = √(B₀² + B₉₀²)
   - This represents the magnitude of the magnetic field vector.

5. **Current Direction Estimation**:
   - The current direction is perpendicular to the magnetic field direction.
   - For visualization, we use the angle directly in the cosine/sine components:
     - U = cos(θ)    # x-component of the current direction
     - V = sin(θ)    # y-component of the current direction

6. **Visualization**:
   - Plot streamlines showing the estimated current flow patterns.
   - Use the field intensity to modulate the color and width of the streamlines.
   - Thicker, brighter streamlines indicate stronger currents.

### Limitations and Considerations

- This method provides a 2D approximation of current flow, not accounting for vertical currents.
- The estimation accuracy depends on the signal-to-noise ratio of the measurements.
- Field distortions near PCB edges or large components may affect the results.
- Combined file (scan_v1a_400MHz_Rx_pcb_combined.json) should not be used for current calculation as it doesn't preserve the original angle information.

## Practical Usage

To visualize current directions:
1. Perform scans at all three orientations (0°, 45°, and 90°)
2. Load the data using the selector interface
3. Click the "Show Currents" button
4. The resulting streamlines represent estimated current flow patterns on the PCB

### Alternative Field Orientation Method

An alternative approach for calculating field orientation uses a more conventional vector angle formula with the 45° measurement specifically for resolving phase ambiguity:

1. **Basic Vector Angle**:
   - First calculate the preliminary angle using standard vector components:
     θ_prelim = arctan2(B₉₀, B₀)
   - This gives the basic orientation of the field vector from orthogonal components.

2. **Phase Ambiguity Resolution**:
   - The arctan2 function has a 180° ambiguity that the 45° measurement can resolve.
   - Calculate expected 45° component based on the preliminary angle:
     B₄₅_expected = (B₀ + B₉₀)/√2
   - Compare with actual 45° measurement to determine if angle needs correction:
     If (B₄₅ · B₄₅_expected) < 0:
       θ_corrected = θ_prelim + π
     Else:
       θ_corrected = θ_prelim

3. **Complete Formula**:
   - θ = arctan2(B₉₀, B₀) + π · step(-B₄₅ · ((B₀ + B₉₀)/√2))
   - Where step(x) is 1 for x > 0 and 0 for x ≤ 0

4. **Advantages**:
   - More intuitive separation between angle calculation and ambiguity resolution
   - May be more robust when B₄₅ values are very small
   - Clearer relationship to classical vector angle calculations

This approach may provide improved results in certain scenarios, especially where the 45° component is weak or noisy. The current direction calculation (steps 5-6 in the Implementation Process) remains the same regardless of which angle estimation method is used.