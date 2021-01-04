import sys

from crossword import *
# Python standard library modules
from itertools import combinations
import math


class CrosswordCreator():

    def __init__(self, crossword):
        """
        Create new CSP crossword generate.
        """
        self.crossword = crossword
        self.domains = {
            var: self.crossword.words.copy()
            for var in self.crossword.variables
        }

    def letter_grid(self, assignment):
        """
        Return 2D array representing a given assignment.
        """
        letters = [
            [None for _ in range(self.crossword.width)]
            for _ in range(self.crossword.height)
        ]
        for variable, word in assignment.items():
            direction = variable.direction
            for k in range(len(word)):
                i = variable.i + (k if direction == Variable.DOWN else 0)
                j = variable.j + (k if direction == Variable.ACROSS else 0)
                letters[i][j] = word[k]
        return letters

    def print(self, assignment):
        """
        Print crossword assignment to the terminal.
        """
        letters = self.letter_grid(assignment)
        for i in range(self.crossword.height):
            for j in range(self.crossword.width):
                if self.crossword.structure[i][j]:
                    print(letters[i][j] or " ", end="")
                else:
                    print("█", end="")
            print()

    def save(self, assignment, filename):
        """
        Save crossword assignment to an image file.
        """
        from PIL import Image, ImageDraw, ImageFont
        cell_size = 100
        cell_border = 2
        interior_size = cell_size - 2 * cell_border
        letters = self.letter_grid(assignment)

        # Create a blank canvas
        img = Image.new(
            "RGBA",
            (self.crossword.width * cell_size,
             self.crossword.height * cell_size),
            "black"
        )
        font = ImageFont.truetype("assets/fonts/OpenSans-Regular.ttf", 80)
        draw = ImageDraw.Draw(img)

        for i in range(self.crossword.height):
            for j in range(self.crossword.width):

                rect = [
                    (j * cell_size + cell_border,
                     i * cell_size + cell_border),
                    ((j + 1) * cell_size - cell_border,
                     (i + 1) * cell_size - cell_border)
                ]
                if self.crossword.structure[i][j]:
                    draw.rectangle(rect, fill="white")
                    if letters[i][j]:
                        w, h = draw.textsize(letters[i][j], font=font)
                        draw.text(
                            (rect[0][0] + ((interior_size - w) / 2),
                             rect[0][1] + ((interior_size - h) / 2) - 10),
                            letters[i][j], fill="black", font=font
                        )

        img.save(filename)

    def solve(self):
        """
        Enforce node and arc consistency, and then solve the CSP.
        """
        self.enforce_node_consistency()
        self.ac3()
        return self.backtrack(dict())

    def enforce_node_consistency(self):
        """
        Update `self.domains` such that each variable is node-consistent.
        (Remove any values that are inconsistent with a variable's unary
         constraints; in this case, the length of the word.)
        """
        # Loops through each Variable object
        for v in self.domains:
            # Loops through each word in each Variable object
            for x in self.domains[v].copy():
                # If inconsistent length, remove word from Variable's domain
                if len(x) != v.length:
                    self.domains[v].remove(x)

    def revise(self, x, y):
        """
        Make variable `x` arc consistent with variable `y`.
        To do so, remove values from `self.domains[x]` for which there is no
        possible corresponding value for `y` in `self.domains[y]`.

        Return True if a revision was made to the domain of `x`; return
        False if no revision was made.
        """
        revised = False

        # All x values of variable x
        xs = list(self.domains[x])
        # All y values of variable y
        ys = list(self.domains[y])
        o = self.crossword.overlaps[x, y]

        if o is not None:
            # (x[i], x)
            xl = [(xs[n][o[0]], xs[n]) for n in range(len(xs))]
            # y[j]
            yl = [ys[n][o[1]] for n in range(len(ys))]
            #print(xl, yl)

            for xw in xl:
                # Inconsistent overlap
                if xw[0] not in yl:
                    self.domains[x].remove(xw[1])
                    revised = True

        return revised

    def ac3(self, arcs=None):
        """
        Update `self.domains` such that each variable is arc consistent.
        If `arcs` is None, begin with initial list of all arcs in the problem.
        Otherwise, use `arcs` as the initial list of arcs to make consistent.

        Return True if arc consistency is enforced and no domains are empty;
        return False if one or more domains end up empty.
        """
        if arcs is None:
            # All arcs (x, y)
            queue = list(combinations(self.domains, 2))
        else:
            # Given arcs
            queue = arcs
        #print(queue)

        while queue != []:
            for arc in queue:
                # Dequeue
                queue.remove(arc)
                #print(arc, arc[0], arc[1])
                if self.revise(x = arc[0], y = arc[1]):
                    # If all values are removed from domain
                    if len(self.domains[arc[0]]) == 0:
                        return False
                    for z in self.crossword.neighbors(arc[0]):
                        # Enqueue
                        queue.append((z, arc[0]))

        return True

    def assignment_complete(self, assignment):
        """
        Return True if `assignment` is complete (i.e., assigns a value to each
        crossword variable); return False otherwise.
        """
        for v in self.domains:
            # Not all variables have been assigned a value
            if v not in assignment.keys():
                return False

        # 1 variable: 1 value in assignment
        return True

    def consistent(self, assignment):
        """
        Return True if `assignment` is consistent (i.e., words fit in crossword
        puzzle without conflicting characters); return False otherwise.
        """
        # Check distinct values
        duplicates = {i for i in assignment for j in assignment if assignment[i] == assignment[j] and i != j}
        if duplicates != set():
            return False

        # Check correct length
        for v in assignment:
            if len(assignment[v]) != v.length:
                return False

        # Check right overlaps
        # Arcs (x, y)
        cs = list(combinations(assignment, 2))
        #print("cs", cs)
        for c in cs:
            o = self.crossword.overlaps[c[0], c[1]]
            if o is not None:
                # Check matching letters
                if assignment[c[0]][o[0]] != assignment[c[1]][o[1]]:
                    return False

        return True

    def order_domain_values(self, var, assignment):
        """
        Return a list of values in the domain of `var`, in order by
        the number of values they rule out for neighboring variables.
        The first value in the list, for example, should be the one
        that rules out the fewest values among the neighbors of `var`.
        """
        dv = []
        count = 0
        neighbors = {v for v in self.crossword.neighbors(var) if v not in assignment}
        
        # Only one possible value for var
        if len(self.domains[var]) == 1:
            return list(self.domains[var])
        
        # Multiple possible values for var
        for value in self.domains[var]:
            for n in neighbors:
                o = self.crossword.overlaps[var, n]
                if o is not None:
                    for n_value in self.domains[n]:
                        if value[o[0]] != n_value[o[1]]:
                            count += 1
            dv.append((count, value))
            # Reset count
            count = 0
        
        # Sort by count in (count, value)
        s = sorted(dv, key=lambda i: i[0])
        order_dv = []
        for i in range(len(s)):
            order_dv.append(s[i][1])

        return order_dv

    def select_unassigned_variable(self, assignment):
        """
        Return an unassigned variable not already part of `assignment`.
        Choose the variable with the minimum number of remaining values
        in its domain. If there is a tie, choose the variable with the highest
        degree. If there is a tie, any of the tied variables are acceptable
        return values.
        """
        # [(len(values), variable)]
        l = [(len(v), k) for k,v in self.domains.items() if k not in assignment]
        # Sort by # of remaining values from low to high
        unassigned = sorted(l, key=lambda kv: kv[0])

        min = unassigned[0][0]
        min_rv = []
        for i in range(len(unassigned)):
            if unassigned[i][0] == min:
                # Append all variables with min remaining domain values
                min_rv.append(unassigned[i][1])
            if unassigned[i][0] > min:
                break
        
        # No tie
        if len(min_rv) == 1:
            return min_rv[0]

        # Tie
        if len(min_rv) > 1:
            max = -math.inf
            max_degrees = []
            for v in min_rv:
                neighbors = self.crossword.neighbors(v)
                if len(neighbors) >= max:
                    max = len(neighbors)
                    max_degrees.append((len(neighbors), v))
            s = sorted(max_degrees, key=lambda k: k[0], reverse=True)
        
        # Return (first) variable with min remaining values and max degrees
        return s[0][1]

    def backtrack(self, assignment):
        """
        Using Backtracking Search, take as input a partial assignment for the
        crossword and return a complete assignment if possible to do so.

        `assignment` is a mapping from variables (keys) to words (values).

        If no assignment is possible, return None.
        """
        if self.assignment_complete(assignment) is True:
            return assignment
        
        var = self.select_unassigned_variable(assignment)
        for value in self.order_domain_values(var, assignment):
            copy = assignment.copy()
            copy[var] = value
            if self.consistent(copy) is True:
                assignment[var] = value
                a = {v for v in self.domains if v not in assignment}
                arcs = list(combinations(a, 2))

                inferences = self.ac3(arcs)
                if inferences is True:
                    result = self.backtrack(assignment)
                    if result is not None:
                        return result
                assignment.remove(var)

        # Failure
        return None

def main():

    # Check usage
    if len(sys.argv) not in [3, 4]:
        sys.exit("Usage: python generate.py structure words [output]")

    # Parse command-line arguments
    structure = sys.argv[1]
    words = sys.argv[2]
    output = sys.argv[3] if len(sys.argv) == 4 else None

    # Generate crossword
    crossword = Crossword(structure, words)
    creator = CrosswordCreator(crossword)
    assignment = creator.solve()

    # Print result
    if assignment is None:
        print("No solution.")
    else:
        creator.print(assignment)
        if output:
            creator.save(assignment, output)


if __name__ == "__main__":
    main()
