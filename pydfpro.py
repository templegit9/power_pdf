import argparse
import os # Added for path manipulation
from PyPDF2 import PdfMerger, PdfReader, PdfWriter # Added PdfReader, PdfWriter
import fitz  # PyMuPDF

def handle_merge(args):
    if len(args.input_files) < 2:
        print("Error: At least two input files are required for merging.")
        return

    merger = PdfMerger()

    try:
        for pdf_file in args.input_files:
            merger.append(pdf_file)
        
        merger.write(args.output_file)
        merger.close()
        print(f"Successfully merged {len(args.input_files)} PDF files into '{args.output_file}'")
    except FileNotFoundError as e:
        print(f"Error: Input file not found - {e.filename}")
    except Exception as e:
        print(f"An error occurred during merging: {e}")

def _parse_page_ranges(ranges_str, total_pages):
    """Parses a page range string (e.g., '1-3,5,7-9') into a list of sets of 0-indexed page numbers.
       Each set in the list corresponds to a new output PDF.
       Validates page numbers against total_pages.
    """
    parsed_range_sets = []
    if not ranges_str:
        return parsed_range_sets

    range_parts = ranges_str.split(',')
    for part in range_parts:
        part = part.strip()
        current_set = set()
        if '-' in part:
            start, end = part.split('-', 1)
            try:
                start_idx = int(start) - 1
                end_idx = int(end) - 1
                if not (0 <= start_idx < total_pages and 0 <= end_idx < total_pages and start_idx <= end_idx):
                    raise ValueError(f"Invalid page range: {part}. Pages must be between 1 and {total_pages}.")
                current_set.update(range(start_idx, end_idx + 1))
            except ValueError as e:
                # Catch errors from int() conversion or our custom validation
                raise ValueError(f"Invalid format in range part: '{part}'. {e}")
        else:
            try:
                page_idx = int(part) - 1
                if not (0 <= page_idx < total_pages):
                    raise ValueError(f"Invalid page number: {part}. Page must be between 1 and {total_pages}.")
                current_set.add(page_idx)
            except ValueError as e:
                raise ValueError(f"Invalid format in page number: '{part}'. {e}")
        if current_set:
            parsed_range_sets.append(sorted(list(current_set))) # Keep pages sorted for each output file
    return parsed_range_sets

def _generate_output_filename(input_path, output_spec, page_num_or_range_suffix, part_num):
    base_name, ext = os.path.splitext(os.path.basename(input_path))
    
    if os.path.isdir(output_spec):
        # Output is a directory, create filename based on original and suffix
        return os.path.join(output_spec, f"{base_name}_{page_num_or_range_suffix}{ext}")
    elif '%%d' in output_spec: 
        # Output is a pattern, use it with part_num
        return output_spec.replace('%%d', str(part_num))
    elif output_spec == ".": # Default case, output to current directory
        return os.path.join(os.getcwd(), f"{base_name}_{page_num_or_range_suffix}{ext}")
    else:
        # Specific filename pattern, potentially with %%d for part number
        if '%' in output_spec : # if it looks like a pattern with only one part
             return output_spec.replace('%%d', str(part_num)) 
        # if it is just a name for a single file output (e.g. for a single range)
        # or the first part of a series if no pattern is given but multiple files will be created
        if part_num > 1 and not '%%d' in output_spec:
            name, e = os.path.splitext(output_spec)
            return f"{name}_{part_num}{e}"
        return output_spec

def handle_split(args):
    try:
        reader = PdfReader(args.input_file)
        total_pages = len(reader.pages)
        output_part_num = 1

        if args.each_page:
            for i in range(total_pages):
                writer = PdfWriter()
                writer.add_page(reader.pages[i])
                
                output_filename_suffix = f"page_{i+1}"
                output_filename = _generate_output_filename(args.input_file, args.output_path, output_filename_suffix, output_part_num)
                output_part_num +=1

                with open(output_filename, "wb") as f:
                    writer.write(f)
                print(f"Created '{output_filename}'")
            print(f"Successfully split PDF into {total_pages} individual pages.")
        elif args.every_n_pages:
            if args.every_n_pages <= 0:
                print("Error: Number of pages for splitting (N) must be a positive integer.")
                return
            
            for i in range(0, total_pages, args.every_n_pages):
                writer = PdfWriter()
                start_page = i
                end_page = min(i + args.every_n_pages, total_pages)
                
                for page_num in range(start_page, end_page):
                    writer.add_page(reader.pages[page_num])
                
                output_filename_suffix = f"pages_{start_page+1}-{end_page}"
                output_filename = _generate_output_filename(args.input_file, args.output_path, output_filename_suffix, output_part_num)
                output_part_num += 1

                with open(output_filename, "wb") as f:
                    writer.write(f)
                print(f"Created '{output_filename}'")
            print(f"Successfully split PDF every {args.every_n_pages} pages.")
        elif args.ranges:
            page_sets_to_extract = _parse_page_ranges(args.ranges, total_pages)
            if not page_sets_to_extract:
                print("No valid page ranges provided or parsed.")
                return

            for page_set in page_sets_to_extract:
                if not page_set: continue # Should not happen if _parse_page_ranges is correct
                
                writer = PdfWriter()
                # Determine suffix for filename based on the range
                if len(page_set) == 1:
                    range_suffix = f"page_{page_set[0]+1}"
                else:
                    # Create a compact representation for ranges, e.g., 1-3_5_7-8
                    # This is a simplified version for now, actual PRD asks for 1-5, 6-10 type splits
                    # The _parse_page_ranges already splits these into separate sets for separate files.
                    # So, the suffix here will be for pages within ONE output file.
                    range_suffix = f"pages_{page_set[0]+1}-{page_set[-1]+1}"
                    # A more robust suffix might list out non-contiguous parts if they end up in same file by some logic
                    # but current logic of _parse_page_ranges makes each comma sep part a new file.

                for page_num in page_set:
                    writer.add_page(reader.pages[page_num])
                
                output_filename = _generate_output_filename(args.input_file, args.output_path, range_suffix, output_part_num)
                output_part_num += 1
                
                with open(output_filename, "wb") as f:
                    writer.write(f)
                print(f"Created '{output_filename}' for pages: { ', '.join(str(p+1) for p in page_set) }")
            print(f"Successfully split PDF by specified ranges.")

    except FileNotFoundError:
        print(f"Error: Input file '{args.input_file}' not found.")
    except Exception as e:
        print(f"An error occurred during splitting: {e}")

def handle_reorder(args):
    try:
        reader = PdfReader(args.input_file)
        total_pages = len(reader.pages)
        writer = PdfWriter()

        # Parse page_order string (1-indexed) into a list of 0-indexed page numbers
        try:
            new_order_indices = [int(p.strip()) - 1 for p in args.page_order.split(',')]
        except ValueError:
            print("Error: Invalid page order string. Must be comma-separated numbers (e.g., \"3,1,2\").")
            return

        # Validate page numbers
        if not all(0 <= idx < total_pages for idx in new_order_indices):
            print(f"Error: Invalid page numbers in order. Pages must be between 1 and {total_pages}.")
            return
        
        # Optional: Check for duplicate page numbers or if all pages are covered, based on stricter requirements
        # For now, allows selecting a subset of pages in a new order.
        # If the PRD implies all original pages must be present, add a check here.

        for page_idx in new_order_indices:
            writer.add_page(reader.pages[page_idx])

        output_filename = args.output_file if args.output_file else args.input_file
        
        # Ensure output directory exists if a path is specified
        if args.output_file and os.path.dirname(args.output_file) and not os.path.exists(os.path.dirname(args.output_file)):
            os.makedirs(os.path.dirname(args.output_file), exist_ok=True)
            
        with open(output_filename, "wb") as f:
            writer.write(f)
        
        action = "Reordered and saved to" if args.output_file else "Reordered (overwritten)"
        print(f"Successfully {action} '{output_filename}'")

    except FileNotFoundError:
        print(f"Error: Input file '{args.input_file}' not found.")
    except Exception as e:
        print(f"An error occurred during reordering: {e}")

def _parse_pages_to_set(pages_str, total_pages):
    """Parses a page string (e.g., '1,3-5,7') into a single set of 0-indexed page numbers.
       Validates page numbers against total_pages.
    """
    pages_to_act_on = set()
    if not pages_str:
        return pages_to_act_on

    parts = pages_str.split(',')
    for part in parts:
        part = part.strip()
        if '-' in part:
            start, end = part.split('-', 1)
            try:
                start_idx = int(start) - 1
                end_idx = int(end) - 1
                if not (0 <= start_idx < total_pages and 0 <= end_idx < total_pages and start_idx <= end_idx):
                    raise ValueError(f"Invalid page range: {part}. Pages must be between 1 and {total_pages}.")
                pages_to_act_on.update(range(start_idx, end_idx + 1))
            except ValueError as e:
                raise ValueError(f"Invalid format in range part: '{part}'. {e}")
        else:
            try:
                page_idx = int(part) - 1
                if not (0 <= page_idx < total_pages):
                    raise ValueError(f"Invalid page number: {part}. Page must be between 1 and {total_pages}.")
                pages_to_act_on.add(page_idx)
            except ValueError as e:
                raise ValueError(f"Invalid format in page number: '{part}'. {e}")
    return pages_to_act_on

def handle_delete(args):
    try:
        reader = PdfReader(args.input_file)
        total_pages = len(reader.pages)
        writer = PdfWriter()

        pages_to_delete_indices = _parse_pages_to_set(args.pages_to_delete, total_pages)

        if not pages_to_delete_indices and args.pages_to_delete.strip(): # Non-empty input string but parsed to empty set implies error already handled by _parse_pages_to_set via raising ValueError
            # This path might not be hit if _parse_pages_to_set raises an error that's caught by the outer try-except
            # However, if it somehow returns empty without raising for a non-empty string, this is a fallback.
            print(f"Warning: No valid pages found to delete based on input '{args.pages_to_delete}'. No changes made.")
            # return # Or proceed to write the original content if that's desired.

        for i in range(total_pages):
            if i not in pages_to_delete_indices:
                writer.add_page(reader.pages[i])
        
        if len(writer.pages) == total_pages and pages_to_delete_indices:
             print(f"Warning: Specified pages to delete ('{args.pages_to_delete}') were not found or were invalid. No pages were deleted.")
        elif not writer.pages and total_pages > 0:
            print("Error: All pages were selected for deletion. Cannot create an empty PDF. No changes made.")
            return

        output_filename = args.output_file if args.output_file else args.input_file

        if args.output_file and os.path.dirname(args.output_file) and not os.path.exists(os.path.dirname(args.output_file)):
            os.makedirs(os.path.dirname(args.output_file), exist_ok=True)

        with open(output_filename, "wb") as f:
            writer.write(f)
        
        action = "saved to" if args.output_file else "(overwritten)"
        num_deleted = total_pages - len(writer.pages)
        if num_deleted > 0 : 
            print(f"Successfully deleted {num_deleted} page(s). Output {action} '{output_filename}'")
        else:
            print(f"No pages were deleted. Output {action} '{output_filename}' (contains original pages).")

    except FileNotFoundError:
        print(f"Error: Input file '{args.input_file}' not found.")
    except ValueError as e: # Catch specific validation errors from _parse_pages_to_set
        print(f"Error: {e}")
    except Exception as e:
        print(f"An error occurred during page deletion: {e}")

def handle_rotate(args):
    try:
        reader = PdfReader(args.input_file)
        writer = PdfWriter()
        total_pages = len(reader.pages)

        pages_to_rotate_indices = set()
        if args.pages: # If specific pages are given
            pages_to_rotate_indices = _parse_pages_to_set(args.pages, total_pages)
        else: # If no pages specified, rotate all pages
            pages_to_rotate_indices = set(range(total_pages))
        
        if not pages_to_rotate_indices and args.pages:
            # This case handles if args.pages was provided but parsed to an empty set due to invalid input
            # _parse_pages_to_set would have raised an error, caught by the ValueError handler below.
            # If it somehow didn't, this is a safeguard, though less likely.
            print(f"Warning: No valid pages found to rotate from input '{args.pages}'. Original PDF will be saved.")

        for i in range(total_pages):
            page = reader.pages[i]
            if i in pages_to_rotate_indices:
                # PyPDF2's page.rotate() rotates clockwise and modifies the page object directly.
                # The angle argument is already validated by argparse choices.
                page.rotate(args.angle)
            writer.add_page(page)

        output_filename = args.output_file if args.output_file else args.input_file

        if args.output_file and os.path.dirname(args.output_file) and not os.path.exists(os.path.dirname(args.output_file)):
            os.makedirs(os.path.dirname(args.output_file), exist_ok=True)

        with open(output_filename, "wb") as f:
            writer.write(f)

        action = "saved to" if args.output_file else "(overwritten)"
        if pages_to_rotate_indices: # Check if any rotation was intended
            print(f"Successfully rotated specified page(s) by {args.angle} degrees. Output {action} '{output_filename}'")
        else: # Should only happen if args.pages was empty and we intended to rotate all, or if args.pages was invalid and caught.
            print(f"No pages were specified for rotation or pages were invalid. Output {action} '{output_filename}' (original or with all pages rotated if --pages omitted).")
            if not args.pages: # If --pages was omitted, all pages were rotated
                 print(f"Successfully rotated all pages by {args.angle} degrees. Output {action} '{output_filename}'")

    except FileNotFoundError:
        print(f"Error: Input file '{args.input_file}' not found.")
    except ValueError as e: # Catch specific validation errors from _parse_pages_to_set
        print(f"Error: {e}")
    except Exception as e:
        print(f"An error occurred during page rotation: {e}")

def handle_extract_text(args):
    try:
        doc = fitz.open(args.input_file)
        text = ""
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text += page.get_text()
        doc.close()

        # Ensure output directory exists
        output_dir = os.path.dirname(args.output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        with open(args.output_file, "w", encoding="utf-8") as f:
            f.write(text)
        
        print(f"Successfully extracted text from '{args.input_file}' to '{args.output_file}'")

    except FileNotFoundError:
        print(f"Error: Input PDF file '{args.input_file}' not found.")
    except Exception as e:
        print(f"An error occurred during text extraction: {e}")

def handle_extract_images(args):
    try:
        doc = fitz.open(args.input_file)
        img_count = 0

        if not os.path.exists(args.output_dir):
            os.makedirs(args.output_dir, exist_ok=True)

        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            image_list = page.get_images(full=True)
            
            for img_index, img_info in enumerate(image_list):
                xref = img_info[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                image_ext = base_image["ext"]

                # Use specified format if possible, otherwise stick to original or PNG as a robust default
                save_ext = args.image_format.lower()
                if image_ext.lower() == save_ext or save_ext == "png": # Prioritize original or PNG
                    final_ext = image_ext if save_ext != "png" else "png"
                else:
                    final_ext = save_ext # Attempt user specified format

                image_filename = os.path.join(args.output_dir, f"image_p{page_num+1}_{img_index+1}.{final_ext}")
                
                try:
                    if final_ext != image_ext: # Requires conversion via Pixmap
                        pix = fitz.Pixmap(image_bytes)
                        if final_ext == "jpg":
                             pix.save(image_filename, "jpeg") # PyMuPDF uses "jpeg" for jpg
                        else:
                             pix.save(image_filename, final_ext)
                        del pix # Release memory
                    else: # Save directly
                        with open(image_filename, "wb") as img_file:
                            img_file.write(image_bytes)
                    img_count += 1
                    print(f"Saved: {image_filename}")
                except Exception as e_save:
                    print(f"Could not save image {image_filename} in format {final_ext} (original: {image_ext}). Error: {e_save}")
                    # Fallback to PNG if conversion failed for some reason
                    if final_ext != "png":
                        try:
                            fallback_filename = os.path.join(args.output_dir, f"image_p{page_num+1}_{img_index+1}_fallback.png")
                            pix = fitz.Pixmap(image_bytes)
                            pix.save(fallback_filename)
                            del pix
                            img_count += 1
                            print(f"Saved fallback as: {fallback_filename}")
                        except Exception as e_fallback:
                            print(f"Could not save fallback PNG for image_p{page_num+1}_{img_index+1}. Error: {e_fallback}")

        doc.close()
        if img_count > 0:
            print(f"Successfully extracted {img_count} image(s) to '{args.output_dir}'")
        else:
            print(f"No images found in '{args.input_file}' or images could not be extracted.")

    except FileNotFoundError:
        print(f"Error: Input PDF file '{args.input_file}' not found.")
    except Exception as e:
        print(f"An error occurred during image extraction: {e}")

def _generate_image_output_filename(base_input_path, output_spec, page_num, desired_ext):
    """Generates an output filename for PDF-to-Image conversion.
    - base_input_path: Original PDF filename (for deriving name if needed).
    - output_spec: User's output path (can be dir or pattern like 'img_%%d.png').
    - page_num: 1-indexed page number.
    - desired_ext: The image extension (e.g., 'png', 'jpg').
    """
    base_name_pdf, _ = os.path.splitext(os.path.basename(base_input_path))

    if '%%d' in output_spec: # User provided a pattern
        # Ensure the pattern's extension matches the desired format, or warn/override?
        # For now, assume user pattern is for the filename stem, we append correct ext.
        pattern_base, pattern_ext = os.path.splitext(output_spec)
        filename_stem = pattern_base.replace('%%d', str(page_num))
        # If pattern had an ext, and it's different, it's a bit ambiguous. Let's prioritize desired_ext.
        final_filename = f"{filename_stem}.{desired_ext}"
        # If output_spec was a directory path in disguise (e.g. "output_dir/page_%%d")
        # os.path.dirname will get the dir part. Then we construct full path.
        if os.path.dirname(output_spec): # check if output_spec contains directory path
            return os.path.join(os.path.dirname(output_spec), os.path.basename(final_filename))
        return final_filename
    elif os.path.isdir(output_spec) or output_spec.endswith('/') or output_spec.endswith('\\\\'):
        # User provided a directory
        if not os.path.exists(output_spec):
            os.makedirs(output_spec, exist_ok=True)
        return os.path.join(output_spec, f"{base_name_pdf}_page_{page_num}.{desired_ext}")
    else:
        # Assumed to be a full filename pattern for the first page, or a generic prefix
        # If it doesn't contain %%d, we append page number for subsequent pages
        name_part, ext_part = os.path.splitext(output_spec)
        if page_num > 1:
            return f"{name_part}_page_{page_num}.{desired_ext}"
        else: # For the first page, or if only one page is converted using a full name
            return f"{name_part}.{desired_ext}"

def handle_pdf_to_image(args):
    try:
        doc = fitz.open(args.input_file)
        total_pages_in_doc = len(doc)
        pages_to_convert_indices = set()

        if args.pages:
            pages_to_convert_indices = _parse_pages_to_set(args.pages, total_pages_in_doc)
            if not pages_to_convert_indices and args.pages.strip():
                 # Error already raised by _parse_pages_to_set and caught by ValueError below
                return 
        else:
            pages_to_convert_indices = set(range(total_pages_in_doc))

        if not pages_to_convert_indices:
            print("No pages selected for conversion.")
            doc.close()
            return
        
        output_format = args.format.lower()
        if output_format == "jpg":
            output_format = "jpeg" # PyMuPDF uses 'jpeg' for saving JPEGs

        converted_count = 0
        for i, page_idx in enumerate(sorted(list(pages_to_convert_indices))): # Process in page order
            page = doc.load_page(page_idx)
            pix = page.get_pixmap(dpi=args.dpi)
            
            # Use 1-based indexing for page numbers in filenames if pattern allows (i.e. %%d)
            # or if it's a directory output.
            # For _generate_image_output_filename, page_num is the actual page number (1-indexed).
            output_filename = _generate_image_output_filename(args.input_file, args.output_dir_or_pattern, page_idx + 1, args.format.lower())
            
            # Ensure output directory exists if part of a pattern or explicit dir
            output_dir = os.path.dirname(output_filename)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)
            
            pix.save(output_filename, output_format)
            print(f"Saved page {page_idx+1} to '{output_filename}'")
            converted_count += 1
            del pix # Release memory

        doc.close()
        if converted_count > 0:
            print(f"Successfully converted {converted_count} page(s) to images.")
        else:
            print(f"No pages were converted from '{args.input_file}'.")

    except FileNotFoundError:
        print(f"Error: Input PDF file '{args.input_file}' not found.")
    except ValueError as e: # Catch specific validation errors from _parse_pages_to_set
        print(f"Error: Invalid page selection - {e}")
    except Exception as e:
        print(f"An error occurred during PDF to image conversion: {e}")

def handle_images_to_pdf(args):
    try:
        doc = fitz.open() # Create a new empty PDF
        img_processed_count = 0

        for img_path in args.input_files:
            try:
                if not os.path.exists(img_path):
                    print(f"Warning: Image file '{img_path}' not found. Skipping.")
                    continue
                
                img_doc = fitz.open(img_path) # Open image file
                rect = img_doc[0].rect # Get image dimensions
                pdf_bytes = img_doc.convert_to_pdf() # Convert image to a 1-page PDF
                img_doc.close()
                
                img_pdf = fitz.open("pdf", pdf_bytes) # Open the 1-page PDF in memory
                doc.insert_pdf(img_pdf) # Insert the image's PDF page into the main document
                img_pdf.close()
                img_processed_count +=1
                print(f"Added '{img_path}' to PDF.")
            except Exception as e_img:
                print(f"Warning: Could not process image '{img_path}'. Error: {e_img}. Skipping.")

        if img_processed_count > 0:
            # Ensure output directory exists
            output_dir = os.path.dirname(args.output_file)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)
            
            doc.save(args.output_file, garbage=4, deflate=True, clean=True)
            print(f"Successfully created PDF '{args.output_file}' from {img_processed_count} image(s).")
        else:
            print("No images were processed. Output PDF not created.")
        
        doc.close()

    except Exception as e:
        print(f"An error occurred during images to PDF conversion: {e}")

def _parse_color_string(color_str):
    try:
        r, g, b = map(float, color_str.split(','))
        if not all(0 <= val <= 1 for val in [r, g, b]):
            raise ValueError("Color values must be between 0 and 1.")
        return (r, g, b)
    except ValueError as e:
        raise ValueError(f"Invalid color string '{color_str}'. Expected R,G,B floats (e.g., \"0.5,0.5,0.5\"). Error: {e}")

def handle_add_watermark(args):
    if not (args.text or args.image):
        print("Error: You must specify either --text or --image for the watermark.")
        return
    if args.text and args.image:
        print("Error: Please specify either --text or --image, not both.")
        return

    try:
        doc = fitz.open(args.input_file)
        total_pages = len(doc)

        target_pages_indices = _parse_pages_to_set(args.pages, total_pages) if args.pages else set(range(total_pages))

        if not target_pages_indices and args.pages:
            print(f"Warning: No valid pages found from input '{args.pages}' to apply watermark.")
            # Save original if no pages matched, or let it save an unchanged doc.
            # For now, let it proceed, will save an unchanged doc effectively.

        for page_idx in target_pages_indices:
            page = doc.load_page(page_idx)
            page_rect = page.rect
            
            # Common properties
            opacity = max(0.0, min(1.0, args.opacity)) # Clamp opacity 0-1
            rotation = args.rotate

            if args.text:
                try:
                    text_color = _parse_color_string(args.color)
                except ValueError as e_color:
                    print(f"Error: {e_color}")
                    doc.close()
                    return
                
                font_name = args.font_name.lower()
                # PyMuPDF font name mapping (basic internal fonts)
                # More sophisticated font handling (e.g., custom fonts) would require font file paths.
                # For simplicity, map to some known PyMuPDF base14 font names or similar.
                # Common ones: helv (Helvetica), timb (Times), cour (Courier)
                # fitz.Font("cjk") for CJK, fitz.Font("arabic") for Arabic etc.
                # We assume user provides a name PyMuPDF can understand for base fonts.
                # For full robustness, check font availability or use specific font files.
                
                # Calculate text width to help with centering/positioning
                # This is an approximation; exact bbox is better if needed.
                text_len = fitz.get_text_length(args.text, fontname=font_name, fontsize=args.font_size)
                tw = text_len
                th = args.font_size # Approximation for height

                # Default to fill_opacity for text, as it's more common for watermarks
                fill_opacity = opacity
                # stroke_opacity = opacity # if we wanted outlined text too

                # Position calculation (simplified)
                # TODO: Implement more robust positioning based on args.position and text/image dimensions
                x, y = 0, 0
                if args.position == "center":
                    x = (page_rect.width - tw) / 2
                    y = (page_rect.height - th) / 2 + th # Y is usually baseline
                elif args.position == "bottom-right":
                    x = page_rect.width - tw - th #  th as a margin
                    y = page_rect.height - th 
                # ... add other positions ...
                elif args.position == "diagonal":
                    # For diagonal, typically rotate and center
                    x = page_rect.width / 2
                    y = page_rect.height / 2
                    if rotation == 0: rotation = -45 # Default diagonal rotation if not specified by user

                # Using insert_textbox for better control over rotation and opacity
                # rect for textbox needs to be large enough if rotated.
                # For simplicity, making a rect around the center for now.
                if args.position == "diagonal":
                     # Diagonal often means centered with rotation
                    rect_w = max(page_rect.width, page_rect.height) # Ensure rect is large enough
                    watermark_rect = fitz.Rect(page_rect.center.x - rect_w/2, page_rect.center.y - rect_w/4, 
                                               page_rect.center.x + rect_w/2, page_rect.center.y + rect_w/4)
                else: # simplified rect for other positions
                    margin = 20 # Generic margin
                    watermark_rect = fitz.Rect(margin, margin, page_rect.width - margin, page_rect.height - margin)
                
                # Note: PyMuPDF text insertion opacity is fill_opacity
                page.insert_textbox(watermark_rect, args.text, fontname=font_name, fontsize=args.font_size, 
                                    color=text_color, fill_opacity=fill_opacity, 
                                    rotate=rotation, align=fitz.TEXT_ALIGN_CENTER if args.position=="center" or args.position=="diagonal" else fitz.TEXT_ALIGN_LEFT)

            elif args.image:
                try:
                    img_doc = fitz.open(args.image)
                    img_rect = img_doc[0].rect
                    img_bytes = img_doc[0].get_pixmap(alpha=True if opacity < 1.0 else False).tobytes("png") # Ensure alpha for opacity
                    img_doc.close()

                    # Position and size for the image watermark
                    # This is a simplified placement, e.g. centered and scaled if too large
                    # TODO: Implement more robust positioning & scaling from args.position
                    target_w, target_h = img_rect.width, img_rect.height
                    scale_factor = 1.0
                    if target_w > page_rect.width / 2:
                        scale_factor = (page_rect.width / 2) / target_w
                    if target_h * scale_factor > page_rect.height / 2:
                        scale_factor = min(scale_factor, (page_rect.height / 2) / target_h)
                    
                    target_w *= scale_factor
                    target_h *= scale_factor

                    x = (page_rect.width - target_w) / 2
                    y = (page_rect.height - target_h) / 2
                    if args.position == "bottom-right":
                         x = page_rect.width - target_w - 20 # 20 as margin
                         y = page_rect.height - target_h - 20
                    # ... other positions
                    
                    img_watermark_rect = fitz.Rect(x, y, x + target_w, y + target_h)

                    page.insert_image(img_watermark_rect, stream=img_bytes, overlay=True, rotate=rotation, opacity=opacity)
                except FileNotFoundError:
                    print(f"Error: Watermark image file '{args.image}' not found.")
                    doc.close()
                    return
                except Exception as e_img:
                    print(f"Error processing watermark image '{args.image}': {e_img}")
                    doc.close()
                    return

        doc.save(args.output_file, garbage=3, deflate=True)
        print(f"Successfully added watermark to '{args.input_file}' and saved to '{args.output_file}'")
        doc.close()

    except FileNotFoundError:
        print(f"Error: Input PDF file '{args.input_file}' not found.")
    except Exception as e:
        print(f"An error occurred during watermarking: {e}")

def handle_add_page_numbers(args):
    try:
        doc = fitz.open(args.input_file)
        total_doc_pages = len(doc) # Total pages in the original document

        target_pages_indices = _parse_pages_to_set(args.pages, total_doc_pages) if args.pages else set(range(total_doc_pages))

        if not target_pages_indices and args.pages:
            print(f"Warning: No valid pages found from input '{args.pages}' to add page numbers.")
        
        try:
            font_color = _parse_color_string(args.font_color)
        except ValueError as e_color:
            print(f"Error: {e_color}")
            doc.close()
            return

        page_num_counter = args.start_number
        processed_pages_for_numbering_count = 0

        for page_idx in range(total_doc_pages):
            if page_idx not in target_pages_indices:
                continue # Skip pages not in the target set

            page = doc.load_page(page_idx)
            page_rect = page.rect
            margin = 20 # Default margin from edge
            
            current_page_text = args.format_string.replace("{page_num}", str(page_num_counter)).replace("{total_pages}", str(total_doc_pages))
            # For {total_pages}, it might be more accurate to use len(target_pages_indices) if numbering only a subset and that subset is considered the new total.
            # However, PRD implies total pages of the document. For now, using total_doc_pages.
            
            text_len = fitz.get_text_length(current_page_text, fontname=args.font_name, fontsize=args.font_size)
            th = args.font_size # Text height approximation

            pos_y = 0
            align = fitz.TEXT_ALIGN_CENTER # Default alignment

            if "footer" in args.position:
                pos_y = page_rect.height - margin - th/2 # Y for textbox bottom, adjust if th is baseline or full height
            elif "header" in args.position:
                pos_y = margin + th/2
            
            pos_x = 0
            if "left" in args.position:
                pos_x = margin
                align = fitz.TEXT_ALIGN_LEFT
            elif "center" in args.position:
                pos_x = (page_rect.width - text_len) / 2
                align = fitz.TEXT_ALIGN_CENTER
            elif "right" in args.position:
                pos_x = page_rect.width - margin - text_len
                align = fitz.TEXT_ALIGN_RIGHT

            # Define a point for text insertion, or a small rect for textbox for more control
            # Using insert_text for simplicity for page numbers here
            # page.insert_text(fitz.Point(pos_x, pos_y), current_page_text, 
            #                    fontname=args.font_name, fontsize=args.font_size, color=font_color)
            
            # Using insert_textbox for potentially better alignment handling within a defined box
            # The rectangle needs to be defined according to the alignment. X positions above are start of text for insert_text.
            # For textbox, x is start of box. For center/right align, this means box x needs to be 0 or page_rect.width respectively.
            box_width = page_rect.width - 2 * margin
            box_x_start = margin
            if align == fitz.TEXT_ALIGN_CENTER:
                # Full width box, text centered within it
                pass # box_x_start = margin, box_width is fine
            elif align == fitz.TEXT_ALIGN_RIGHT:
                # Full width box, text right-aligned within it
                pass # box_x_start = margin, box_width is fine
            elif align == fitz.TEXT_ALIGN_LEFT:
                pass # box_x_start = margin, box_width is fine

            # Define the textbox rectangle
            # Ensure Y position makes sense: if pos_y is for text baseline, rect bottom should be pos_y - font_size, top is pos_y.
            # PyMuPDF y is from top. So header_y should be small, footer_y large.
            if "footer" in args.position: 
                textbox_y_bottom = page_rect.height - margin
                textbox_y_top = textbox_y_bottom - args.font_size * 1.5 # Box height slightly larger than font
            else: # Header
                textbox_y_top = margin
                textbox_y_bottom = textbox_y_top + args.font_size * 1.5

            textbox_rect = fitz.Rect(box_x_start, textbox_y_top, box_x_start + box_width, textbox_y_bottom)

            page.insert_textbox(textbox_rect, current_page_text, 
                                fontname=args.font_name, fontsize=args.font_size, color=font_color, 
                                align=align)

            page_num_counter += 1
            processed_pages_for_numbering_count +=1

        if processed_pages_for_numbering_count > 0:
            doc.save(args.output_file, garbage=3, deflate=True)
            print(f"Successfully added page numbers to {processed_pages_for_numbering_count} page(s) in '{args.input_file}' and saved to '{args.output_file}'")
        else:
            print(f"No pages were selected or processed for page numbering. Output file '{args.output_file}' may be unchanged or empty if input was empty.")
            # Optionally save even if no pages processed, to reflect an empty or original doc
            # doc.save(args.output_file, garbage=3, deflate=True) 
        doc.close()

    except FileNotFoundError:
        print(f"Error: Input PDF file '{args.input_file}' not found.")
    except Exception as e:
        print(f"An error occurred during page numbering: {e}")

def handle_encrypt(args):
    if not args.user_password and not args.owner_password:
        print("Error: You must specify at least a user password or an owner password to encrypt the PDF.")
        return

    try:
        reader = PdfReader(args.input_file)
        writer = PdfWriter()

        for page in reader.pages:
            writer.add_page(page)

        # Determine effective owner password
        owner_pwd = args.owner_password if args.owner_password else args.user_password

        # PyPDF2 permissions are typically set by *not* allowing them (False means restricted)
        # The PRD defines permissions as "allow_xxx", so we need to invert the logic for PyPDF2's model
        # if PyPDF2 expects True for "can do X" and False for "cannot do X".
        # Let's check PyPDF2 docs or common usage. 
        # PyPDF2's writer.encrypt() permissions parameter: A list of operations NOT allowed.
        # So, if args.allow_print == "yes", it should NOT be in the permissions list for PyPDF2.
        # This is complex. Let's try to map directly. 
        # The `permissions_flag` in PyPDF2's `encrypt` method uses flags that are set if allowed.
        # For example, `UserAccessPermissions.PRINT` (which is 4)
        # We need to construct the integer flag based on args.
        # Let's use the direct permission flags if available or common practice for PyPDF2 > v3.
        # PyPDF2's `writer.encrypt()` has `permissions_flag` argument which expects an integer.
        # This integer is a bitwise combination of flags defined in `PyPDF2.generic.UserAccessPermissions`.

        # For PyPDF2, the `permissions` argument to `encrypt` is a bit confusing historically.
        # In modern PyPDF2 (>=3.0.0), `encrypt` takes `user_password`, `owner_password`,
        # and `permissions_flag` (integer). The `permissions_flag` is a bitmask of allowed operations.
        # We will assume PyPDF2 version >= 3.0.0 for the `permissions_flag` approach.
        # If using an older version, the permission model might be different (e.g., based on what's *not* allowed).
        
        # Standard PDF permissions flags (these are typical values, PyPDF2 should have constants for these):
        # Bit 3 (1<<2): Print (high and low res allowed if set)
        # Bit 4 (1<<3): Modify contents (other than annotations/forms)
        # Bit 5 (1<<4): Copy text and graphics
        # Bit 6 (1<<5): Add or modify text annotations and interactive form fields
        # PyPDF2 uses `UserAccessPermissions` enum/object for this.
        # For simplicity here, let's assume direct mapping and that higher level PyPDF2 handles this well.
        # Actually, PyPDF2 `encrypt` method does NOT directly take boolean allow_print etc.
        # It takes `user_pwd`, `owner_pwd`, and then it depends on the library version how permissions are set.
        # Some versions had `permissions=` with a list of disallowed operations.
        # Newer versions (like PyPDF2 `3.0.0+` via `pypdf`) use `permissions_flag` as an int.
        # Let's stick to what's generally expected by a modern PdfWriter.encrypt method.
        # The `encrypt` method in `PyPDF2.PdfWriter` (as of PyPDF2 3.0.0 / pypdf 3.x.x)
        # takes `user_password`, `owner_password`, and `use_128bit` (True for 128-bit, False for 40-bit, default True).
        # For AES encryption (AES-128, AES-256), we need to use different parameters, or ensure the library handles it.
        # PyPDF2's `encrypt` is for standard security handler. AES is usually specified by algorithm code.

        # According to PyPDF2 documentation for `PdfWriter.encrypt()`:
        # It sets standard security. AES is not directly chosen by a simple boolean.
        # The strength ('128' or '256') often implies the algorithm if supported by the version. PyPDF2's base `encrypt` does RC4.
        # For specific AES, often one might need to delve deeper or use a library that exposes this choice more directly if PyPDF2's default `encrypt` isn't AES.
        # However, the PRD says "Uses standard PDF encryption (e.g., AES-128 or AES-256)".
        # Most modern PDF libraries encrypting with 128-bit or 256-bit keys will use AES by default or as an option.
        # PyPDF2's `encrypt` method itself, particularly in older versions, used RC4. 
        # For pypdf (the successor/current PyPDF2), `writer.encrypt(user_password, owner_password, strength="128/256")` might be the way.
        # Let's assume the installed PyPDF2 (>=3.0) or pypdf handles strength argument correctly for AES.

        # The permission flags for PyPDF2 (pypdf) are more complex if we want fine-grained control as in the PRD.
        # `writer.encrypt(user_pwd, owner_pwd, permissions_flag=calculated_flags, strength="128" or "256")`
        # The `permissions_flag` is an integer. Let's try to construct it based on common PDF flags.
        # Bits: 2=print, 3=modify, 4=copy, 5=annotate. (0-indexed bits)
        perm_flag = 0
        if args.allow_print == "yes":
            perm_flag |= (1 << 2) # Allow Printing
            # PyPDF2 also has flags for high-quality printing etc. For simplicity, general print.
        if args.allow_modify == "yes":
            perm_flag |= (1 << 3) # Allow Modify contents (other than annotations/forms)
        if args.allow_copy == "yes":
            perm_flag |= (1 << 4) # Allow Copy text and graphics
        if args.allow_annotate == "yes":
            perm_flag |= (1 << 5) # Allow Add or modify text annotations and interactive form fields
            perm_flag |= (1 << 10) # Allow form field fill-in or signing (often grouped with annotations)

        # PyPDF2's `encrypt` method might not directly use `permissions_flag` in all underlying versions.
        # Some take a list of strings for `permissions`.
        # Let's go with a more direct call that PyPDF2 versions generally support or `pypdf` uses.
        # The PRD mentions AES-128 or AES-256. PyPDF2 `encrypt` method's `use_128bit` boolean is relevant.
        # If `args.encryption_strength == 256`, this is a stronger encryption than default 128bit RC4.
        # `pypdf` handles `strength='256'` argument. If we are using strict `PyPDF2<3`, this might not work directly.
        # For now, let's assume the installed version supports strength or the boolean for 128bit.

        # Simplified approach for permissions, assuming PyPDF2 can take them more directly or uses a default set if not specified.
        # The PRD acceptance criteria: "User can set an owner password and define permissions (e.g., printing, copying, modifying)."
        # This implies we should be able to control these specific permissions.
        # However, PyPDF2's PdfWriter.encrypt method parameters are `user_password`, `owner_password=None`, `use_128bit=True`.
        # It does NOT have direct flags for allow_print etc. in its main signature for older versions.
        # Permissions are often controlled by what the *owner* can do vs the *user*.
        # The `permissions_flag` is the way to go for `pypdf`.
        # If using an older PyPDF2, it might be `encrypt(user_pwd, owner_pwd, permissions=['print', 'modify'])` where permissions is a list of *allowed* actions.
        # This is highly dependent on the exact PyPDF2/pypdf version and its API for `encrypt`.

        # Given that `pypdf` is the modern continuation of PyPDF2, let's write for its `encrypt` signature which supports strength and permissions_flag.
        # If this fails, it indicates an older PyPDF2 might be in use or the API is different.
        # For `pypdf`: `encrypt(self, user_password: str, owner_password: Optional[str] = None, permissions: Optional[Permissions] = None, strength: Literal['40', '128', '256'] = '128')`
        # `Permissions` is an Enum. Let's try to map our args to that.

        # Re-checking PyPDF2 (specifically, if the environment has 'PyPDF2' and not 'pypdf')
        # `PdfWriter.encrypt(user_password, owner_password=None, use_128bit=True)`
        # This version of encrypt in classic PyPDF2 does NOT have fine-grained permission flags directly.
        # The permissions are implicitly full for owner, and restricted for user if only user_pw is set.
        # To set specific user permissions, it was more complex, sometimes involving direct manipulation of the encryption dictionary.

        # Given the PRD, we need to control these. If direct PyPDF2 `encrypt` doesn't do this easily, 
        # using `fitz` (PyMuPDF) is a better choice as it offers clear permission settings.
        # `doc.save(output_path, encryption=fitz.PDF_ENCRYPT_AES_256, owner_pw=owner, user_pw=user, permissions=perm_int)`

        # Let's use fitz (PyMuPDF) for encryption as it provides clearer control over AES and permissions
        # as per PRD requirements.

        perm = 0
        # PyMuPDF permission flags (fitz.PDF_PERM_PRINT etc.)
        if args.allow_print == "yes":
            perm |= fitz.PDF_PERM_PRINT
        if args.allow_modify == "yes":
            perm |= fitz.PDF_PERM_MODIFY
        if args.allow_copy == "yes":
            perm |= fitz.PDF_PERM_COPY
        if args.allow_annotate == "yes":
            perm |= fitz.PDF_PERM_ANNOTATE
            perm |= fitz.PDF_PERM_FILLFORM # Often grouped
        
        # PyMuPDF encryption algorithm choices
        encryption_method = fitz.PDF_ENCRYPT_AES_128
        if args.encryption_strength == 256:
            encryption_method = fitz.PDF_ENCRYPT_AES_256
        elif args.encryption_strength == 128:
            encryption_method = fitz.PDF_ENCRYPT_AES_128
        # else default to 128 per our arg default

        # PyMuPDF save with encryption:
        # doc.save(filename, encryption, user_password, owner_password, permissions)
        # We need to re-open the input with fitz and save it. PyPDF2 writer was for page copying, not needed if fitz handles all.
        
        doc_to_encrypt = fitz.open(args.input_file) # Open with fitz
        doc_to_encrypt.save(
            args.output_file,
            encryption=encryption_method,
            user_pw=args.user_password if args.user_password else "", # User pw can be empty if owner_pw is set
            owner_pw=owner_pwd if owner_pwd else "", # Owner pw can be empty if user_pw is set (but PRD implies one is needed)
            permissions=perm
        )
        doc_to_encrypt.close()

        print(f"Successfully encrypted '{args.input_file}' and saved to '{args.output_file}'")
        print(f"  User Password: {'Set' if args.user_password else 'Not set'}")
        print(f"  Owner Password: {'Set' if owner_pwd else 'Not set'}")
        print(f"  Permissions: Print({args.allow_print}), Modify({args.allow_modify}), Copy({args.allow_copy}), Annotate({args.allow_annotate})")
        print(f"  Encryption Strength: {args.encryption_strength}-bit AES")

    except FileNotFoundError:
        print(f"Error: Input PDF file '{args.input_file}' not found.")
    except Exception as e:
        print(f"An error occurred during PDF encryption: {e}")

def handle_decrypt(args):
    try:
        doc = fitz.open(args.input_file)
        if doc.is_encrypted:
            if doc.authenticate(args.password):
                # Successfully authenticated, now save without encryption
                # To save without encryption, simply call save without encryption parameters
                doc.save(args.output_file)
                print(f"Successfully decrypted '{args.input_file}' and saved to '{args.output_file}'")
            else:
                print(f"Error: Incorrect password for '{args.input_file}'. Decryption failed.")
        else:
            print(f"Info: File '{args.input_file}' is not encrypted. Saving a copy to '{args.output_file}'.")
            doc.save(args.output_file) # Save a copy even if not encrypted, as per typical behavior
        
        doc.close()

    except FileNotFoundError:
        print(f"Error: Input PDF file '{args.input_file}' not found.")
    except fitz.errors.FitzAuthError: # Specific error for PyMuPDF authentication issues
        print(f"Error: Authentication failed for '{args.input_file}'. This might be due to an incorrect password or a damaged file.")
    except Exception as e:
        print(f"An error occurred during PDF decryption: {e}")

def handle_compress(args):
    try:
        doc = fitz.open(args.input_file)
        
        # Define save parameters based on compression level
        save_kwargs = {
            "garbage": 4,       # Remove unused objects (0-4, higher is more thorough)
            "clean": True,        # Clean and sanitize content streams
            "deflate": True,      # Compress streams (requires zlib)
            # "deflate_images": True, # Optionally re-compress images (can be lossy or slow)
            # "deflate_fonts": True,  # Optionally re-compress embedded fonts
            "linear": False,      # Linearized PDFs are for fast web view, can be larger
            "pretty": False,      # Pretty-printing makes it larger
        }

        if args.level == "strong":
            save_kwargs["garbage"] = 4 # Max garbage collection
            # For "strong" compression, we could also consider options like downsampling images
            # or converting them to more efficient formats if they are not already.
            # This would require iterating through pages and images, which is more complex
            # than just save options. For now, strong will use max garbage collection and aggressive deflate.
            # save_kwargs["deflate_images"] = True # Example: this could be lossy depending on original format
            # save_kwargs["deflate_fonts"] = True
            print("Using strong compression settings.")
        else: # Basic compression
            save_kwargs["garbage"] = 3 # Slightly less aggressive garbage collection
            print("Using basic compression settings.")

        # Ensure output directory exists
        output_dir = os.path.dirname(args.output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        doc.save(args.output_file, **save_kwargs)
        doc.close()

        original_size = os.path.getsize(args.input_file)
        compressed_size = os.path.getsize(args.output_file)
        reduction = original_size - compressed_size
        reduction_percent = (reduction / original_size) * 100 if original_size > 0 else 0

        print(f"Successfully compressed '{args.input_file}' and saved to '{args.output_file}'")
        print(f"  Original size: {original_size / 1024:.2f} KB")
        print(f"  Compressed size: {compressed_size / 1024:.2f} KB")
        print(f"  Reduction: {reduction / 1024:.2f} KB ({reduction_percent:.2f}%)")

    except FileNotFoundError:
        print(f"Error: Input PDF file '{args.input_file}' not found.")
    except Exception as e:
        print(f"An error occurred during PDF compression: {e}")

def main():
    parser = argparse.ArgumentParser(description="PyDF Pro: A Python PDF Utility", prog="pydfpro")
    parser.set_defaults(func=lambda args: parser.print_help()) # Default action: print help

    subparsers = parser.add_subparsers(title="Commands", dest="command", help="Available commands")

    # FP-001: Merge PDFs
    merge_parser = subparsers.add_parser("merge", help="Merge multiple PDF files into a single document.")
    merge_parser.add_argument("input_files", nargs="+", help="Two or more PDF files to merge.")
    merge_parser.add_argument("-o", "--output_file", required=True, help="Path for the output merged PDF file.")
    merge_parser.set_defaults(func=handle_merge)

    # FP-002: Split PDF
    split_parser = subparsers.add_parser("split", help="Split a PDF document into multiple files.")
    split_parser.add_argument("input_file", help="The PDF file to split.")
    split_parser.add_argument("-o", "--output_path", default=".", help="Directory or filename pattern for output files (e.g., output_%%d.pdf or output_dir/). Defaults to current directory with original_filename_page_%%d.pdf pattern.")
    split_group = split_parser.add_mutually_exclusive_group(required=True)
    split_group.add_argument("-r", "--ranges", help="Specify page ranges to extract (e.g., \"1-5,8,10-12\"). Each range becomes a new PDF.")
    split_group.add_argument("-n", "--every_n_pages", type=int, metavar="N", help="Split the PDF every N pages.")
    split_group.add_argument("-e", "--each_page", action="store_true", help="Split each page into an individual PDF file.")
    split_parser.set_defaults(func=handle_split) # Connect handle_split function

    # FP-003: Reorder Pages
    reorder_parser = subparsers.add_parser("reorder", help="Reorder pages in a PDF document.")
    reorder_parser.add_argument("input_file", help="The PDF file to reorder.")
    reorder_parser.add_argument("page_order", help="New page order as a comma-separated list of 1-indexed page numbers (e.g., \"3,1,2,4\").")
    reorder_parser.add_argument("-o", "--output_file", help="Path for the output reordered PDF file. If omitted, overwrites the input file.")
    reorder_parser.set_defaults(func=handle_reorder) # Connect handle_reorder function

    # FP-004: Delete Pages
    delete_parser = subparsers.add_parser("delete", help="Delete pages from a PDF document.")
    delete_parser.add_argument("input_file", help="The PDF file to modify.")
    delete_parser.add_argument("pages_to_delete", help="Comma-separated page numbers or ranges to delete (e.g., \"1,3-5,7\").")
    delete_parser.add_argument("-o", "--output_file", help="Path for the output PDF file. If omitted, overwrites the input file.")
    delete_parser.set_defaults(func=handle_delete) # Connect handle_delete function

    # FP-005: Rotate Pages
    rotate_parser = subparsers.add_parser("rotate", help="Rotate pages in a PDF document.")
    rotate_parser.add_argument("input_file", help="The PDF file to modify.")
    rotate_parser.add_argument("angle", type=int, choices=[90, 180, 270], help="Rotation angle in degrees (90, 180, 270 clockwise).")
    rotate_parser.add_argument("-p", "--pages", help="Comma-separated page numbers or ranges to rotate (e.g., \"1,3-5,7\"). Defaults to all pages if not specified.")
    rotate_parser.add_argument("-o", "--output_file", help="Path for the output PDF file. If omitted, overwrites the input file.")
    rotate_parser.set_defaults(func=handle_rotate) # Connect handle_rotate function

    # FP-006: Extract Text
    extract_text_parser = subparsers.add_parser("extract-text", help="Extract all text content from a PDF into a plain text file (.txt).")
    extract_text_parser.add_argument("input_file", help="The PDF file to extract text from.")
    extract_text_parser.add_argument("-o", "--output_file", required=True, help="Path for the output .txt file.")
    extract_text_parser.set_defaults(func=handle_extract_text) # Connect handler

    # FP-007: Extract Images
    extract_images_parser = subparsers.add_parser("extract-images", help="Extract images embedded within a PDF file.")
    extract_images_parser.add_argument("input_file", help="The PDF file to extract images from.")
    extract_images_parser.add_argument("-o", "--output_dir", required=True, help="Directory to save extracted images.")
    extract_images_parser.add_argument("--image_format", default="png", choices=["png", "jpg", "bmp", "tiff"], help="Preferred format for saving images if conversion is possible (default: png). Note: Images are typically extracted in their original format or a common lossless format.")
    extract_images_parser.set_defaults(func=handle_extract_images) # Connect handler

    # FP-008: PDF to Image
    pdf_to_image_parser = subparsers.add_parser("pdf-to-image", help="Convert PDF pages to image files (PNG, JPG).")
    pdf_to_image_parser.add_argument("input_file", help="The PDF file to convert.")
    pdf_to_image_parser.add_argument("-o", "--output_dir_or_pattern", required=True, help="Directory or filename pattern for output images (e.g., output_dir/ or page_%%d.png).")
    pdf_to_image_parser.add_argument("-p", "--pages", help="Comma-separated page numbers or ranges to convert (e.g., \"1,3-5,7\"). Defaults to all pages.")
    pdf_to_image_parser.add_argument("--format", default="png", choices=["png", "jpg"], help="Output image format (default: png).")
    pdf_to_image_parser.add_argument("--dpi", type=int, default=150, help="Dots Per Inch (DPI) for the output images (default: 150).")
    pdf_to_image_parser.set_defaults(func=handle_pdf_to_image) # Connect handler

    # FP-009: Image(s) to PDF
    images_to_pdf_parser = subparsers.add_parser("images-to-pdf", help="Convert one or more image files (JPG, PNG) into a single PDF document.")
    images_to_pdf_parser.add_argument("input_files", nargs='+', help="One or more image files (e.g., *.jpg, image1.png image2.jpeg).")
    images_to_pdf_parser.add_argument("-o", "--output_file", required=True, help="Path for the output PDF file.")
    # images_to_pdf_parser.add_argument("--layout", default="one_per_page", choices=["one_per_page", "multiple_per_page"], help="Layout of images in PDF (default: one_per_page).") # For future enhancement for multiple images per page
    images_to_pdf_parser.set_defaults(func=handle_images_to_pdf)

    # FP-010: Add Watermark
    add_watermark_parser = subparsers.add_parser("add-watermark", help="Add a text or image watermark to PDF pages.")
    add_watermark_parser.add_argument("input_file", help="The PDF file to watermark.")
    add_watermark_parser.add_argument("-o", "--output_file", required=True, help="Path for the output watermarked PDF file.")
    add_watermark_parser.add_argument("--text", help="Text for the watermark.")
    add_watermark_parser.add_argument("--image", help="Path to an image file for the watermark.")
    # Arguments for text watermark properties
    add_watermark_parser.add_argument("--font_name", default="helv", help="Font name for text watermark (e.g., helv, timb, cour). Default: helv (Helvetica).")
    add_watermark_parser.add_argument("--font_size", type=int, default=48, help="Font size for text watermark. Default: 48.")
    add_watermark_parser.add_argument("--color", default="0.5,0.5,0.5", help="Text color as R,G,B floats (0-1, e.g., \"1,0,0\" for red). Default: gray (0.5,0.5,0.5).")
    add_watermark_parser.add_argument("--opacity", type=float, default=0.5, help="Opacity for watermark (0.0 to 1.0). Default: 0.5.")
    add_watermark_parser.add_argument("--position", default="center", choices=["center", "top-left", "top-center", "top-right", "bottom-left", "bottom-center", "bottom-right", "diagonal"], help="Position of the watermark. Default: center.")
    add_watermark_parser.add_argument("--rotate", type=float, default=0, help="Rotation angle for the watermark in degrees. Default: 0.")
    add_watermark_parser.add_argument("-p", "--pages", help="Comma-separated page numbers or ranges to apply watermark (e.g., \"1,3-5,7\"). Defaults to all pages.")
    add_watermark_parser.set_defaults(func=handle_add_watermark) # Connect handler

    # FP-011: Add Page Numbers
    add_page_numbers_parser = subparsers.add_parser("add-page-numbers", help="Add page numbers to a PDF.")
    add_page_numbers_parser.add_argument("input_file", help="The PDF file to add page numbers to.")
    add_page_numbers_parser.add_argument("-o", "--output_file", required=True, help="Path for the output PDF file with page numbers.")
    add_page_numbers_parser.add_argument("--position", default="footer-center", 
                                       choices=["footer-left", "footer-center", "footer-right", 
                                                "header-left", "header-center", "header-right"],
                                       help="Position of page numbers (e.g., footer-center). Default: footer-center.")
    add_page_numbers_parser.add_argument("--start_number", type=int, default=1, help="Starting page number. Default: 1.")
    add_page_numbers_parser.add_argument("--font_name", default="helv", help="Font name for page numbers (e.g., helv, timb, cour). Default: helv.")
    add_page_numbers_parser.add_argument("--font_size", type=int, default=10, help="Font size for page numbers. Default: 10.")
    add_page_numbers_parser.add_argument("--font_color", default="0,0,0", help="Font color as R,G,B floats (0-1, e.g., \"0,0,0\" for black). Default: black.")
    add_page_numbers_parser.add_argument("--format_string", default="Page {page_num} of {total_pages}", help="Format string for page number text. Use {page_num} and {total_pages}. Default: \"Page {page_num} of {total_pages}\".")
    add_page_numbers_parser.add_argument("-p", "--pages", help="Comma-separated page numbers or ranges to apply page numbers (e.g., \"1,3-5,7\"). Defaults to all pages.")
    add_page_numbers_parser.set_defaults(func=handle_add_page_numbers) # Connect handler

    # --- Security & Optimization Features ---
    # FP-012: Password Protect (Encrypt)
    encrypt_parser = subparsers.add_parser("encrypt", help="Encrypt a PDF with an owner and/or user password.")
    encrypt_parser.add_argument("input_file", help="The PDF file to encrypt.")
    encrypt_parser.add_argument("-o", "--output_file", required=True, help="Path for the output encrypted PDF file.")
    encrypt_parser.add_argument("--user_password", "-up", help="Password required to open the PDF.")
    encrypt_parser.add_argument("--owner_password", "-op", help="Password required to change permissions or remove other passwords. If not set, user_password will be used if provided.")
    
    encrypt_parser.add_argument("--allow_print", choices=["yes", "no"], default="yes", help="Allow printing? (yes/no). Default: yes.")
    encrypt_parser.add_argument("--allow_modify", choices=["yes", "no"], default="yes", help="Allow modifying the document? (yes/no). Default: yes.")
    encrypt_parser.add_argument("--allow_copy", choices=["yes", "no"], default="yes", help="Allow copying text and graphics? (yes/no). Default: yes.")
    encrypt_parser.add_argument("--allow_annotate", choices=["yes", "no"], default="yes", help="Allow adding/modifying text annotations and interactive form fields? (yes/no). Default: yes.")
    encrypt_parser.add_argument("--encryption_strength", type=int, choices=[128, 256], default=128, help="Encryption key length (128 or 256 bits). Default: 128.")
    encrypt_parser.set_defaults(func=handle_encrypt) # Connect handler

    # FP-013: Remove Password (Decrypt)
    decrypt_parser = subparsers.add_parser("decrypt", help="Remove password protection from a PDF if the password is known.")
    decrypt_parser.add_argument("input_file", help="The encrypted PDF file.")
    decrypt_parser.add_argument("password", help="The password to open the PDF (user or owner password).")
    decrypt_parser.add_argument("-o", "--output_file", required=True, help="Path for the output decrypted PDF file.")
    decrypt_parser.set_defaults(func=handle_decrypt) # Connect handler

    # FP-014: Compress PDF
    compress_parser = subparsers.add_parser("compress", help="Reduce the file size of a PDF.")
    compress_parser.add_argument("input_file", help="The PDF file to compress.")
    compress_parser.add_argument("-o", "--output_file", required=True, help="Path for the output compressed PDF file.")
    compress_parser.add_argument("-l", "--level", default="basic", choices=["basic", "strong"], help="Compression level (basic, strong). Default: basic.")
    compress_parser.set_defaults(func=handle_compress) # Connect handler

    args = parser.parse_args()

    if hasattr(args, 'func'):
        args.func(args)
    else:
        parser.print_help() # Should not happen if subparsers are set up correctly with set_defaults

if __name__ == "__main__":
    main() 