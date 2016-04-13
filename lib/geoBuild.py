#! /usr/bin/python
# -*- coding-utf-8 -*-

import mmap
import yaml
import re

class geoBuild():

    skill_badges = {
            "solder" : ("Souder", "../i/badges/solder.png")
            }

    def __init__(self, doc_in, dir_out = "./doc"):
        self.doc_in = doc_in

        self.doc_out = ""
        self.dir_out = dir_out

        self.f_in = None

        self.header = None
        self.header_limit = -1

        self.items = {}

        # Parsing flags
        self.pf_inP = False

    def __enter__(self):
        """Open the file.
        """
        self.f_in = open(self.doc_in, 'r')
        return self

    def __exit__(self, type, value, traceback):
        """Close the file.
        """
        self.f_in.close()

    def parseHeader(self):
        """Parse the header of the file.
        """

        if self.header_limit < 0:
            f_in_mmap = mmap.mmap(self.f_in.fileno(),
                    0, access=mmap.ACCESS_READ)
            self.header_limit = f_in_mmap.find(b'---')

            if self.header_limit != -1:
                self.header = yaml.load(
                        f_in_mmap[0:self.header_limit])
            else:
                raise("Cannot load the header")

            # Parse the items list for further uses
            for item in self.header["items"]:
                item_dict = {}
                item_dict["name"] = item['name']
                item_dict["qty"] = item['qty']
                item_dict["description"] = item['description']
                item_dict["img_path"] = self.img_path(src=item['img'])

                for item_id in item['id'].split(', '):
                    self.items[item_id] = item_dict


    def parseLine(self, line):
        """Parse a line.
        """

        # Regex
        re_title = re.match("^(#+) (.+)$", line)
        re_img = re.match("^\!\[(.+)\]\((.+)\)$", line)
        re_meta = re.match("^\$(\w+)(: (.+))?$", line)

        rejected = ["---\n"]

        # Init the parsed line
        line_parsed = ""

        if line in rejected:
            line_parsed += ""

        elif re_title:
            line_parsed += self.parse_title(re_title)

        elif re_img:
            line_parsed += self.parse_image(re_img)

        elif re_meta:
            line_parsed += self.parse_meta(re_meta)

        elif line == "\n":
            if self.pf_inP:
                # Close a paragrah
                self.pf_inP = False
                line_parsed += "</p>\n"
            else:
                line_parsed += ""

        else:
            if not self.pf_inP:
                self.pf_inP = True
                line_parsed += "\n<p>"

            line_parsed += "%s " % line[:-1]

        return line_parsed

    def parse(self):
        """Parse all the document.
        """

        # Reset flags
        self.pf_inP = False

        # Parse the header
        self.parseHeader()

        # Init the output file
        self.doc_out = "%s/%s.php" % (
                self.dir_out, self.header['version'])

        with open(self.doc_out, 'w') as f_out:
            # Write down the header
            # ... version
            f_out.write(
                    "<p>Documentation %s</p>\n"
                    % self.header["version"])

            # ... skill bagdes
            skills = self.header.get("skills", [])
            if skills:
                f_out.write(
                        "<section id=\"skillsList\">\n" \
                        "<h2>Compétences</h2>\n" \
                        "<ul>\n")

                for skill, lvl in self.header.get("skills", []):
                    skill_name = geoBuild.skill_badges[skill][0]
                    skill_badge = self.write_img(
                            src=geoBuild.skill_badges[skill][1],
                            alt=skill_name,
                            autoPath=False)
                    f_out.write(
                            "\t<li>\n" \
                            "\t\t<div class=\"skill\">\n" \
                            "\t\t\t%s\n" \
                            "\t\t\t<p class=\"skill_name\">%s</p>" \
                            "\t\t\t<p class=\"skill_lvl\">Niveau %d.</p>" \
                            "\t\t</div>\n" \
                            "\t</li>\n" % (
                                skill_badge, skill_name, lvl))
            f_out.write(
                "</ul>\n" \
                "\n" \
                "</section>\n")


            # ... parts list
            f_out.write("\n")
            f_out.write(
                "<section id=\"partsList\" class=\"partsList\">\n" \
                "<h2>Composants</h2>\n" \
                "<ul>\n")

            for item in self.header["items"]:
                img_path = self.img_path(src=item['img'])
                img = self.write_img(src=img_path,
                        alt=item['description'],
                        autoPath=False)

                f_out.write(
                        "\t<li>\n" \
                        "\t\t<div class=\"item\">\n" \
                        "\t\t\t<a href=\"%s\">\n" \
                        "\t\t\t\t%s\n" \
                        "\t\t\t</a>\n" \
                        "\t\t\t<p class=\"item_name\">%s x%s</p>\n" \
                        "\t\t\t<p class=\"item_description\">%s</p>\n" \
                        "\t\t</div>\n" \
                        "\t</li>\n" % (
                        img_path, img, item['name'], item['qty'], item['description']))

            f_out.write(
                "</ul>\n" \
                "\n" \
                "</section>\n")

            # ... intro
            f_out.write("\n")
            f_out.write(
                "<section id=\"doc\" class=\"doc\">\n" \
                "<h2>Notice de montage</h2>\n")

            # Parse the rest of the document
            self.f_in.seek(self.header_limit)

            for line in self.f_in.readlines():
                # Parse the line
                line_parsed = self.parseLine(line)

                # Write it out
                f_out.write(line_parsed)

            # Close any open paragraph
            if self.pf_inP:
                self.pg_inP = False
                f_out.write("</p>\n")

            # ... ending
            f_out.write("\n")
            f_out.write("</section>")

    # ----------------
    # -- subparsers --
    # ----------------

    def parse_title(self, re_title):
        """Parse a title based on the resuslt of the regex.
        """
        rank = len(re_title.group(1)) + 2
        title = re_title.group(2)

        return "\n<h%d>%s</h%d>\n" % (
                rank, title, rank)

    def parse_image(self, re_img):
        """Parse an image based on the resuslt of the regex.
        """
        src = re_img.group(1)
        alt = re_img.group(2)

        parsed_line  = "\n"
        parsed_line += self.write_img(src, alt)
        parsed_line += "\n"

        return parsed_line

    def parse_meta(self, re_meta):
        """Parse a meta command.
        syntax:
            $cmd
            $cmd: arg1,arg2,...
        eg
            $items: C1,C2
        """

        if len(re_meta.groups()) == 3:
            if re_meta.group(1) == "items":
                item_ids = re_meta.group(3).split(', ')

                parsed_line  = "\n"
                parsed_line += "<div class=\"partsList\"\n>"
                parsed_line += "<ul>\n"
                
                for item_id in item_ids:
                    item = self.items[item_id]

                    img = self.write_img(src=item["img_path"],
                            alt=item['description'],
                            autoPath=False)

                    parsed_line += "" \
                        "\t<li>\n" \
                        "\t\t<div class=\"item\">\n" \
                        "\t\t\t<a href=\"%s\">\n" \
                        "\t\t\t\t%s\n" \
                        "\t\t\t</a>\n" \
                        "\t\t\t<p class=\"item_name\">%s</p>\n" \
                        "\t\t\t<p class=\"item_description\">%s</p>\n" \
                        "\t\t</div>\n" \
                        "\t</li>\n" % (
                        item["img_path"], img, item_id, item['description'])

                parsed_line += "</ul>\n" 
                parsed_line += "</div>\n" 

        return parsed_line


    # -------------
    # -- writers --
    # -------------

    def write_img(self, src, alt="", autoPath = True):
        if autoPath == True:
            src = self.img_path(src)
        return "<img src=\"%s\" alt=\"%s\" />" % (src, alt)

    def img_path(self, src):
        return "../i/doc/%s/%s" % (self.header['long_project_id'], src)
