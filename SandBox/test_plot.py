from sandbox import AICodeSandbox
from PIL import Image

# example plot code i got from chatgpt
plot_code = """
import matplotlib.pyplot as plt
import numpy as np

# Step 1: Create some data
x = np.linspace(0, 10, 500)  # 500 points from 0 to 10 for smooth curves
y1 = np.sin(x)  # Sine wave
y2 = np.cos(x)  # Cosine wave
y3 = np.sin(x) + np.cos(x)  # Combined sine and cosine wave

# Step 2: Create a plot with enhanced features
plt.figure(figsize=(10, 6))  # Set the size of the plot

# Plot multiple lines
plt.plot(x, y1, label='Sine Wave', color='blue', linestyle='-', linewidth=2)
plt.plot(x, y2, label='Cosine Wave', color='red', linestyle='--', linewidth=2)
plt.plot(x, y3, label='Sine + Cosine', color='green', linestyle=':', linewidth=2)

# Add a title and labels
plt.title('Enhanced Plot with Multiple Lines and Annotations', fontsize=14)
plt.xlabel('X-axis', fontsize=12)
plt.ylabel('Y-axis', fontsize=12)

# Add grid and legend
plt.grid(True)  # Show grid
plt.legend(loc='upper right')  # Show legend in the upper right

# Annotate a point
plt.annotate('Intersection Point',
             xy=(7.85, 0),  # Point to annotate
             xytext=(8, 1),  # Text location
             arrowprops=dict(facecolor='black', shrink=0.05))

# Add a horizontal line
plt.axhline(0, color='gray', linestyle='--', linewidth=0.7)

# Customize ticks
plt.xticks(fontsize=10)
plt.yticks(fontsize=10)

# Step 3: Save the plot as a PNG file
plt.savefig('/new.png', format='png', dpi=300)  # Save the plot with high resolution

# Optional: Display the plot
plt.show()

# Notify that the plot was saved
print("Enhanced plot saved as /new.png")




"""



sandbox = AICodeSandbox(packages=['matplotlib', 'numpy'])


# for some reason sandbox akes a buffer to start png file so we need to reset index to correct place
def clean_file(file_path):
    with open(file_path, 'rb') as file:
        data = file.read()
    
    # Find the start of the PNG file signature
    png_signature = b'\x89PNG\r\n\x1a\n'
    start_index = data.find(png_signature)
    
    if start_index != -1:
        # Trim the data to start at the PNG signature
        cleaned_data = data[start_index:]
        with open(file_path, 'wb') as file:
            file.write(cleaned_data)
    else:
        raise ValueError("PNG signature not found in file")

def get_content(file_path):
    with open(file_path, 'rb') as file:
        return file.read()

try:
   

    result = sandbox.run_code(plot_code)
    print(result)

    # Retrieve the plot image
    plot_image = sandbox.read_file('/new.png')

    # Save the plot image to a local file
    with open('new.png', 'wb') as file:
        file.write(plot_image)
    print("Plot saved as new.png")

    # clean file
    clean_file('new.png')
    
    # opens new image
    with Image.open('new.png') as img:
        img.show()


finally:
    # Clean up resources
    sandbox.close()